"""
app/pipeline/nodes/rag_engine.py
----------------------------------
Layer 2B: RAG-based FSSAI Regulatory Engine.

Uses ChromaDB to store FSSAI regulation text and 
Groq LLM to answer regulatory questions about specific products.

Runs AFTER Layer 2A (hardcoded rules) to handle:
- Edge cases not covered by JSON thresholds
- Complex multi-condition rules
- Claims that need legal citation
- Ambiguous marketing language
"""

import json
import time
import chromadb
from chromadb.utils import embedding_functions
from pathlib import Path
from groq import Groq

from app.pipeline.state import NutriGuardState
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# ── ChromaDB Setup ─────────────────────────────────────────────
CHROMA_PATH = Path("./chroma_db")
COLLECTION_NAME = "fssai_regulations"

_chroma_client = None
_collection = None
_groq_client = None


def _get_groq_client():
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=settings.GROQ_API_KEY)
    return _groq_client


def _get_collection():
    """Initialize ChromaDB collection with FSSAI regulations."""
    global _chroma_client, _collection

    if _collection is not None:
        return _collection

    _chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))

    # Use ChromaDB's default embedding function (no external downloads)
    ef = embedding_functions.DefaultEmbeddingFunction()

    _collection = _chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
        metadata={"description": "FSSAI food safety regulations for RAG"}
    )

    # Index regulations if collection is empty
    if _collection.count() == 0:
        logger.info("rag_engine.indexing_regulations")
        _index_regulations()

    return _collection


def _index_regulations():
    """Index all FSSAI regulation text into ChromaDB."""
    from app.data.fssai_regulations import FSSAI_REGULATIONS

    collection = _collection

    documents = []
    metadatas = []
    ids = []

    for reg in FSSAI_REGULATIONS:
        documents.append(reg["text"])
        metadatas.append({
            "source": reg["source"],
            "section": reg["section"],
            "claim_type": reg["claim_type"],
            "id": reg["id"],
        })
        ids.append(reg["id"])

    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids,
    )

    logger.info("rag_engine.indexed", count=len(documents))


def _build_rag_query(claim: str, nutrients: dict, product_name: str) -> str:
    """Build a natural language query for RAG retrieval."""
    nutrient_summary = ", ".join([
        f"{k.replace('_', ' ')}: {v}"
        for k, v in nutrients.items()
        if v is not None
    ])
    return f"FSSAI regulation for claim '{claim}' on product with nutrients: {nutrient_summary}"


def _query_groq_with_context(
    claim: str,
    regulation_text: str,
    nutrients: dict,
    product_name: str,
    ingredients: str = None,
) -> dict:
    """
    Uses Groq LLM to evaluate a claim against retrieved regulation text.
    Returns structured verdict with legal citation.
    """
    nutrient_str = json.dumps({k: v for k, v in nutrients.items() if v is not None}, indent=2)
    ingredients_str = ingredients or "Not available"

    prompt = f"""You are a strict FSSAI food safety compliance expert. 
Your job is to evaluate whether a specific product claim violates Indian food safety regulations.

PRODUCT: {product_name}
CLAIM: "{claim}"
ACTUAL NUTRIENT VALUES (per 100g): {nutrient_str}
INGREDIENTS: {ingredients_str}

RELEVANT FSSAI REGULATION:
{regulation_text}

INSTRUCTIONS:
1. First identify what TYPE of claim this is:
   - QUANTITY claim: makes a specific nutritional promise ("high protein", "low fat", "sugar free")
   - ORIGIN claim: states where an ingredient comes from ("plant protein", "sea salt", "olive oil")
   - PROCESS claim: states how food was made ("baked", "roasted", "cold pressed")
   - WELLNESS claim: implies health benefit ("guilt free", "clean", "superfood")
   - CERTIFICATION claim: implies official certification ("organic", "natural")

2. For ORIGIN and PROCESS claims: only flag if the claim is factually contradicted by ingredients or nutrients
3. For QUANTITY claims: check against the regulation thresholds strictly
4. For WELLNESS claims: check if nutritional profile supports the implied benefit
5. If the claim is vague or subjective with no specific regulation: return UNVERIFIABLE

Return ONLY this JSON, no markdown:
{{
  "claim_type": "QUANTITY/ORIGIN/PROCESS/WELLNESS/CERTIFICATION",
  "verdict": "COMPLIANT" or "NON_COMPLIANT" or "UNVERIFIABLE",
  "reason": "specific explanation referencing actual numbers",
  "regulation_citation": "exact regulation section or null",
  "severity": "CRITICAL" or "HIGH" or "MEDIUM" or "LOW" or null,
  "legal_basis": "one sentence or null"
}}"""

    client = _get_groq_client()
    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        max_tokens=512,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1])

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "claim_type": "UNKNOWN",
            "verdict": "UNVERIFIABLE",
            "reason": "Could not parse LLM response",
            "regulation_citation": None,
            "severity": None,
            "legal_basis": None,
        }

async def rag_engine_node(state: NutriGuardState) -> dict:
    """
    Layer 2B: RAG-based FSSAI compliance checker.

    Handles claims that Layer 2A (hardcoded rules) marked as UNVERIFIABLE.
    Retrieves relevant regulation text from ChromaDB and uses Groq LLM
    to make a legally-cited verdict.
    """
    logger.info("rag_engine.start")
    start_time = time.time()

    extraction = state.get("extraction_result", {})
    regulatory_result = state.get("regulatory_result", {})

    if not extraction:
        return {"rag_result": {"analysed": False, "note": "No extraction data"}}

    # Only process UNVERIFIABLE claims from Layer 2A
    existing_verdicts = regulatory_result.get("claim_verdicts", [])
    unverifiable_claims = [
        v for v in existing_verdicts
        if v.get("verdict") == "UNVERIFIABLE" and v.get("regulation") is None
    ]

    if not unverifiable_claims:
        logger.info("rag_engine.no_unverifiable_claims")
        return {
            "rag_result": {
                "analysed": True,
                "claims_processed": 0,
                "note": "All claims were handled by Layer 2A hardcoded rules",
                "rag_verdicts": [],
            }
        }

    nutrients_per_100g = extraction.get("nutrients_per_100g", {})
    product_name = extraction.get("product_name", "Unknown")

    logger.info("rag_engine.processing_claims", count=len(unverifiable_claims))

    # Initialize ChromaDB
    collection = _get_collection()
    rag_verdicts = []

    for claim_verdict in unverifiable_claims:
        claim = claim_verdict.get("claim", "")
        if not claim or claim.startswith("MANDATORY_CHECK"):
            continue

        try:
            # Retrieve relevant regulations
            query = _build_rag_query(claim, nutrients_per_100g, product_name)
            results = collection.query(
                query_texts=[query],
                n_results=2,
            )

            if not results["documents"] or not results["documents"][0]:
                rag_verdicts.append({
                    "claim": claim,
                    "verdict": "UNVERIFIABLE",
                    "reason": "No matching regulation found in FSSAI database",
                    "source": "rag_engine",
                })
                continue

            # Combine top 2 regulation texts
            regulation_text = "\n\n".join(results["documents"][0])
            sources = [m.get("source", "") for m in results["metadatas"][0]]
            sections = [m.get("section", "") for m in results["metadatas"][0]]

            # Ask Groq to evaluate
            # Ask Groq to evaluate
            verdict = _query_groq_with_context(
                claim=claim,
                regulation_text=regulation_text,
                nutrients=nutrients_per_100g,
                product_name=product_name,
                ingredients=extraction.get("ingredients"),
            )

            verdict["claim"] = claim
            verdict["regulation"] = verdict.get("regulation_citation")
            verdict["source"] = "rag_engine"
            verdict["regulation_sources"] = sources
            verdict["regulation_sections"] = sections

            logger.info(
                "rag_engine.claim_evaluated",
                claim=claim,
                verdict=verdict.get("verdict"),
            )

            rag_verdicts.append(verdict)

        except Exception as e:
            logger.error("rag_engine.claim_error", claim=claim, error=str(e))
            rag_verdicts.append({
                "claim": claim,
                "verdict": "UNVERIFIABLE",
                "reason": f"RAG evaluation error: {str(e)}",
                "source": "rag_engine",
            })

    elapsed_ms = round((time.time() - start_time) * 1000)
    non_compliant = [v for v in rag_verdicts if v.get("verdict") == "NON_COMPLIANT"]

    logger.info(
        "rag_engine.complete",
        claims_processed=len(rag_verdicts),
        non_compliant=len(non_compliant),
        elapsed_ms=elapsed_ms,
    )

    return {
        "rag_result": {
            "analysed": True,
            "claims_processed": len(rag_verdicts),
            "non_compliant": len(non_compliant),
            "rag_verdicts": rag_verdicts,
        }
    }