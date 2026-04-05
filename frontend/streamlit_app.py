"""
frontend/streamlit_app.py
NutriGuard AI — Food Fraud Detection Dashboard
Complete UI with all layers:
- Single / Dual / Triple image modes
- Math Validation
- FSSAI Rules (Layer 2A)
- RAG Engine (Layer 2B)
- NutriScore 2024
- Ingredient Parser
- Hidden Sugar Detector
- PDF Complaint Generator
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import date

import streamlit as st
from PIL import Image
import io

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.pipeline.graph import nutriguard_pipeline
from app.reports.complaint_generator import generate_complaint

# ── Page Config ───────────────────────────────────────────────
st.set_page_config(
    page_title="NutriGuard AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500&display=swap');

* { font-family: 'DM Sans', sans-serif; }

.stApp {
    background: #0a0a0f;
    color: #e8e8f0;
}

h1, h2, h3 { font-family: 'Syne', sans-serif; }

.hero-title {
    font-family: 'Syne', sans-serif;
    font-size: 3.5rem;
    font-weight: 800;
    background: linear-gradient(135deg, #00ff88 0%, #00ccff 50%, #7c3aed 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    line-height: 1.1;
    margin-bottom: 0.5rem;
}

.hero-sub {
    font-family: 'DM Mono', monospace;
    font-size: 0.85rem;
    color: #666680;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-bottom: 2rem;
}

.fraud-score-box {
    border-radius: 16px;
    padding: 2rem;
    text-align: center;
    margin: 1rem 0;
}

.score-minimal { background: linear-gradient(135deg, #0d2818, #1a4a2e); border: 1px solid #00ff88; }
.score-low     { background: linear-gradient(135deg, #1a2a0d, #2e4a1a); border: 1px solid #88ff00; }
.score-medium  { background: linear-gradient(135deg, #2a1a0d, #4a2e1a); border: 1px solid #ffaa00; }
.score-high    { background: linear-gradient(135deg, #2a0d0d, #4a1a1a); border: 1px solid #ff4400; }
.score-critical{ background: linear-gradient(135deg, #1a0000, #3a0000); border: 1px solid #ff0000; }

.score-number {
    font-family: 'Syne', sans-serif;
    font-size: 5rem;
    font-weight: 800;
    line-height: 1;
}

.score-label {
    font-family: 'DM Mono', monospace;
    font-size: 0.9rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    margin-top: 0.5rem;
    opacity: 0.8;
}

.verdict-text {
    font-size: 0.9rem;
    margin-top: 1rem;
    opacity: 0.7;
    font-style: italic;
}

.layer-card {
    background: #12121f;
    border: 1px solid #2a2a3f;
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    margin: 0.5rem 0;
}

.violation-card {
    background: #1a0d0d;
    border-left: 3px solid #ff4400;
    border-radius: 0 8px 8px 0;
    padding: 1rem 1.2rem;
    margin: 0.5rem 0;
    font-size: 0.9rem;
}

.compliant-card {
    background: #0d1a0d;
    border-left: 3px solid #00ff88;
    border-radius: 0 8px 8px 0;
    padding: 1rem 1.2rem;
    margin: 0.5rem 0;
    font-size: 0.9rem;
}

.unverifiable-card {
    background: #12121f;
    border-left: 3px solid #555570;
    border-radius: 0 8px 8px 0;
    padding: 1rem 1.2rem;
    margin: 0.5rem 0;
    font-size: 0.9rem;
    opacity: 0.7;
}

.sugar-card {
    background: #1a1200;
    border-left: 3px solid #ffcc00;
    border-radius: 0 8px 8px 0;
    padding: 1rem 1.2rem;
    margin: 0.5rem 0;
    font-size: 0.9rem;
}

.rag-card {
    background: #0d0d1a;
    border-left: 3px solid #7c3aed;
    border-radius: 0 8px 8px 0;
    padding: 1rem 1.2rem;
    margin: 0.5rem 0;
    font-size: 0.9rem;
}

.additive-high   { color: #ff4444; }
.additive-medium { color: #ffaa44; }
.additive-low    { color: #44ff88; }

.nutriscore-badge {
    display: inline-block;
    width: 60px;
    height: 60px;
    border-radius: 50%;
    font-family: 'Syne', sans-serif;
    font-size: 2rem;
    font-weight: 800;
    line-height: 60px;
    text-align: center;
    color: white;
}

.grade-a { background: #1a9641; }
.grade-b { background: #52b74a; }
.grade-c { background: #f7c027; color: #333; }
.grade-d { background: #f77b00; }
.grade-e { background: #d7191c; }

.metric-row {
    display: flex;
    justify-content: space-between;
    padding: 0.4rem 0;
    border-bottom: 1px solid #1a1a2e;
    font-size: 0.88rem;
}

.metric-label { color: #888899; }
.metric-value  { font-family: 'DM Mono', monospace; color: #e8e8f0; }

.tag-compliant {
    background: #0d2818; color: #00ff88;
    border: 1px solid #00ff8844;
    border-radius: 4px; padding: 2px 8px;
    font-size: 0.75rem; font-family: 'DM Mono', monospace;
}

.tag-violation {
    background: #2a0d0d; color: #ff4444;
    border: 1px solid #ff444444;
    border-radius: 4px; padding: 2px 8px;
    font-size: 0.75rem; font-family: 'DM Mono', monospace;
}

.tag-unknown {
    background: #1a1a2e; color: #888899;
    border: 1px solid #88889944;
    border-radius: 4px; padding: 2px 8px;
    font-size: 0.75rem; font-family: 'DM Mono', monospace;
}

.tag-rag {
    background: #1a0d2a; color: #c084fc;
    border: 1px solid #7c3aed44;
    border-radius: 4px; padding: 2px 8px;
    font-size: 0.75rem; font-family: 'DM Mono', monospace;
}

.tag-sugar {
    background: #1a1200; color: #ffcc00;
    border: 1px solid #ffcc0044;
    border-radius: 4px; padding: 2px 8px;
    font-size: 0.75rem; font-family: 'DM Mono', monospace;
}

div[data-testid="stFileUploader"] {
    background: #0d0d1a;
    border-radius: 12px;
}

.stButton > button {
    background: linear-gradient(135deg, #00ff88, #00ccff);
    color: #0a0a0f;
    border: none;
    border-radius: 8px;
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    font-size: 1rem;
    padding: 0.7rem 2rem;
    width: 100%;
    transition: opacity 0.2s;
}

.stButton > button:hover { opacity: 0.85; }

.stTabs [data-baseweb="tab"] {
    font-family: 'DM Mono', monospace;
    font-size: 0.8rem;
    letter-spacing: 0.1em;
    color: #666680;
}

.stTabs [aria-selected="true"] { color: #00ff88 !important; }

.pdf-box {
    background: #0d1a0d;
    border: 1px solid #00ff8844;
    border-radius: 12px;
    padding: 1.5rem;
    margin: 1rem 0;
}

.mode-badge {
    background: #1a1a2e;
    border: 1px solid #2a2a4a;
    border-radius: 8px;
    padding: 0.3rem 0.8rem;
    font-family: 'DM Mono', monospace;
    font-size: 0.75rem;
    color: #888899;
    display: inline-block;
    margin-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)


# ── Helper Functions ──────────────────────────────────────────

def get_score_class(score: int) -> str:
    if score == 0:    return "score-minimal"
    elif score <= 20: return "score-low"
    elif score <= 40: return "score-medium"
    elif score <= 70: return "score-high"
    return "score-critical"


def get_score_color(score: int) -> str:
    if score == 0:    return "#00ff88"
    elif score <= 20: return "#88ff00"
    elif score <= 40: return "#ffaa00"
    elif score <= 70: return "#ff4400"
    return "#ff0000"


def get_grade_class(grade: str) -> str:
    return f"grade-{grade.lower()}" if grade in "ABCDE" else "grade-c"


# ── Pipeline Runners ──────────────────────────────────────────

async def run_pipeline_single(image_bytes: bytes, filename: str) -> dict:
    return await nutriguard_pipeline.ainvoke({
        "image_bytes": image_bytes,
        "image_filename": filename,
        "pipeline_metadata": {},
    })


async def run_pipeline_dual(
    front_bytes: bytes, front_name: str,
    back_bytes: bytes, back_name: str,
) -> dict:
    return await nutriguard_pipeline.ainvoke({
        "front_image_bytes": front_bytes,
        "front_image_filename": front_name,
        "back_image_bytes": back_bytes,
        "back_image_filename": back_name,
        "pipeline_metadata": {},
    })


async def run_pipeline_triple(
    front_bytes: bytes, front_name: str,
    back_bytes: bytes, back_name: str,
    ingredients_bytes: bytes, ingredients_name: str,
) -> dict:
    return await nutriguard_pipeline.ainvoke({
        "front_image_bytes": front_bytes,
        "front_image_filename": front_name,
        "back_image_bytes": back_bytes,
        "back_image_filename": back_name,
        "ingredients_image_bytes": ingredients_bytes,
        "ingredients_image_filename": ingredients_name,
        "pipeline_metadata": {},
    })


# ── Render Functions ──────────────────────────────────────────

def render_fraud_score(fraud_score: dict):
    score = fraud_score.get("score", 0)
    level = fraud_score.get("level", "MINIMAL")
    interpretation = fraud_score.get("interpretation", "")
    color = get_score_color(score)
    css_class = get_score_class(score)

    st.markdown(f"""
    <div class="fraud-score-box {css_class}">
        <div class="score-number" style="color:{color};">{score}</div>
        <div class="score-label" style="color:{color};">/ 100 — {level}</div>
        <div class="verdict-text">{interpretation}</div>
    </div>
    """, unsafe_allow_html=True)

    signals = fraud_score.get("signals", [])
    if signals:
        st.markdown("**Fraud Signals Detected:**")
        for sig in signals:
            pts = sig.get("points", 0)
            pts_str = f"+{pts} pts" if pts > 0 else "ℹ info"
            source_colors = {
                "regulatory_engine":     "#ff4444",
                "rag_engine":            "#c084fc",
                "nutriscore":            "#00ccff",
                "hidden_sugar_detector": "#ffcc00",
                "ingredient_parser":     "#ffaa44",
                "math_validator":        "#ff8800",
            }
            src_color = source_colors.get(sig["source"], "#888899")
            st.markdown(f"""
            <div class="layer-card">
                <span style="color:{src_color}; font-size:0.75rem; font-family:'DM Mono',monospace;">
                    {sig['source'].upper()} &nbsp;·&nbsp; {pts_str}
                </span><br/>
                <span style="font-size:0.9rem;">{sig['signal']}</span>
            </div>
            """, unsafe_allow_html=True)
            for d in sig.get("details", []):
                st.markdown(f'<div class="violation-card">🚨 {d}</div>', unsafe_allow_html=True)


def render_regulatory(regulatory: dict, rag_result: dict):
    verdicts = regulatory.get("claim_verdicts", [])
    summary = regulatory.get("summary", {})
    rag_verdicts = rag_result.get("rag_verdicts", []) if rag_result else []

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("✅ Compliant",      summary.get("compliant", 0))
    col2.metric("🚨 Non-Compliant",  summary.get("non_compliant", 0))
    col3.metric("❓ Unverifiable",   summary.get("unverifiable", 0))
    col4.metric("🔍 RAG Evaluated",  len(rag_verdicts))

    st.markdown("#### Layer 2A — FSSAI Hardcoded Rules")
    for v in verdicts:
        verdict = v.get("verdict")
        claim   = v.get("claim", "")
        reason  = v.get("reason", "")
        regulation = v.get("regulation", "")
        actual  = v.get("actual_value")
        threshold = v.get("threshold")
        unit    = v.get("unit", "")

        if verdict == "NON_COMPLIANT":
            tag = '<span class="tag-violation">NON-COMPLIANT</span>'
            card_class = "violation-card"
            icon = "🚨"
        elif verdict == "COMPLIANT":
            tag = '<span class="tag-compliant">COMPLIANT</span>'
            card_class = "compliant-card"
            icon = "✅"
        else:
            tag = '<span class="tag-unknown">UNVERIFIABLE</span>'
            card_class = "unverifiable-card"
            icon = "❓"

        details = ""
        if actual is not None and threshold is not None:
            details = f"<br/><span style='font-family:DM Mono,monospace;font-size:0.8rem;opacity:0.7;'>Actual: {actual} {unit} &nbsp;·&nbsp; Threshold: {threshold} {unit}</span>"

        reg_text = f"<br/><span style='font-size:0.75rem;opacity:0.5;'>{regulation}</span>" if regulation else ""

        st.markdown(f"""
        <div class="{card_class}">
            {tag} &nbsp; {icon} <strong>{claim}</strong>
            <br/><span style="font-size:0.85rem;opacity:0.8;">{reason}</span>
            {details}{reg_text}
        </div>
        """, unsafe_allow_html=True)

    if rag_verdicts:
        st.markdown("#### Layer 2B — RAG FSSAI Regulation Database")
        for v in rag_verdicts:
            verdict = v.get("verdict")
            claim   = v.get("claim", "")
            reason  = v.get("reason", "")
            citation = v.get("regulation_citation") or v.get("regulation", "")
            claim_type = v.get("claim_type", "")
            severity = v.get("severity", "")

            if verdict == "NON_COMPLIANT":
                tag = '<span class="tag-violation">NON-COMPLIANT</span>'
                card_class = "violation-card"
                icon = "🚨"
            elif verdict == "COMPLIANT":
                tag = '<span class="tag-compliant">COMPLIANT</span>'
                card_class = "compliant-card"
                icon = "✅"
            else:
                tag = '<span class="tag-unknown">UNVERIFIABLE</span>'
                card_class = "unverifiable-card"
                icon = "❓"

            type_badge = f'<span class="tag-rag">{claim_type}</span>' if claim_type else ""
            sev_badge  = f'<span style="font-size:0.75rem;opacity:0.6;"> · {severity}</span>' if severity else ""
            cite_text  = f"<br/><span style='font-size:0.75rem;opacity:0.5;'>📋 {citation}</span>" if citation else ""

            st.markdown(f"""
            <div class="{card_class}">
                {tag} &nbsp; {icon} <strong>{claim}</strong> &nbsp; {type_badge}{sev_badge}
                <br/><span style="font-size:0.85rem;opacity:0.8;">{reason}</span>
                {cite_text}
            </div>
            """, unsafe_allow_html=True)


def render_nutriscore(nutriscore: dict):
    grade  = nutriscore.get("grade", "?")
    score  = nutriscore.get("score", 0)
    neg    = nutriscore.get("negative_points", {})
    pos    = nutriscore.get("positive_points", {})
    protein_rule = nutriscore.get("protein_rule_applied", False)

    col1, col2 = st.columns([1, 2])

    with col1:
        grade_class = get_grade_class(grade)
        st.markdown(f"""
        <div style="text-align:center; padding:1rem;">
            <div class="nutriscore-badge {grade_class}">{grade}</div>
            <div style="font-family:'DM Mono',monospace;font-size:0.75rem;margin-top:0.5rem;opacity:0.6;">
                NUTRISCORE 2024
            </div>
            <div style="font-family:'Syne',sans-serif;font-size:1.5rem;font-weight:700;margin-top:0.3rem;">
                Score: {score}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("**Negative Points** (unhealthy)")
        for k, v in neg.get("breakdown", {}).items():
            st.markdown(f"""
            <div class="metric-row">
                <span class="metric-label">{k.replace('_',' ').title()}</span>
                <span class="metric-value">{v} pts</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br/>**Positive Points** (healthy)", unsafe_allow_html=True)
        for k, v in pos.get("breakdown", {}).items():
            if k == "protein_raw":
                continue
            st.markdown(f"""
            <div class="metric-row">
                <span class="metric-label">{k.replace('_',' ').title()}</span>
                <span class="metric-value">{v} pts</span>
            </div>
            """, unsafe_allow_html=True)

        if protein_rule:
            st.warning("⚠️ 2024 Rule: Protein points = 0 because N ≥ 11. High-protein junk food cannot game the score.")


def render_ingredients(ingredient: dict):
    if not ingredient.get("analysed"):
        st.info(f"ℹ️ {ingredient.get('note', 'Ingredients not analysed.')}")
        return

    additives = ingredient.get("additives", {})
    allergens = ingredient.get("allergens", [])
    violations = ingredient.get("violations", [])

    if violations:
        st.markdown("**⚠️ Claim-Ingredient Contradictions:**")
        for v in violations:
            st.markdown(f'<div class="violation-card">🚨 {v["message"]}</div>', unsafe_allow_html=True)

    total = additives.get("total_found", 0)
    if total == 0:
        st.success("✅ No concerning additives detected.")
    else:
        st.markdown(f"**{total} Additives Detected:**")
        for a in additives.get("high_concern", []):
            st.markdown(f"""
            <div class="layer-card">
                <span class="additive-high">🔴 HIGH CONCERN</span> &nbsp;
                <strong>{a['code']} — {a['name']}</strong>
                <span style="opacity:0.6;font-size:0.8rem;"> ({a['type']})</span>
                <br/><span style="font-size:0.83rem;opacity:0.7;">{a['notes']}</span>
            </div>
            """, unsafe_allow_html=True)

        for a in additives.get("medium_concern", []):
            st.markdown(f"""
            <div class="layer-card">
                <span class="additive-medium">🟡 MEDIUM CONCERN</span> &nbsp;
                <strong>{a['code']} — {a['name']}</strong>
                <span style="opacity:0.6;font-size:0.8rem;"> ({a['type']})</span>
                <br/><span style="font-size:0.83rem;opacity:0.7;">{a['notes']}</span>
            </div>
            """, unsafe_allow_html=True)

        for a in additives.get("low_concern", []):
            st.markdown(f"""
            <div class="layer-card">
                <span class="additive-low">🟢 LOW CONCERN</span> &nbsp;
                <strong>{a['code']} — {a['name']}</strong>
                <span style="opacity:0.6;font-size:0.8rem;"> ({a['type']})</span>
            </div>
            """, unsafe_allow_html=True)

    if allergens:
        for a in allergens:
            st.markdown(f"""
            <div class="layer-card">
                ⚠️ <strong>Allergen Detected:</strong> {', '.join(a['allergens_detected'])}
                <br/><span style="font-size:0.83rem;opacity:0.7;">{a['message']}</span>
            </div>
            """, unsafe_allow_html=True)


def render_hidden_sugar(hidden_sugar: dict):
    if not hidden_sugar.get("analysed"):
        st.info(f"ℹ️ {hidden_sugar.get('note', 'Hidden sugar analysis not available.')}")
        return

    aliases_found   = hidden_sugar.get("sugar_aliases_found", [])
    alias_count     = hidden_sugar.get("sugar_alias_count", 0)
    splitting       = hidden_sugar.get("sugar_splitting", {})
    position        = hidden_sugar.get("sugar_position_analysis", {})
    high_gi         = hidden_sugar.get("high_gi_ingredients", [])
    sweeteners      = hidden_sugar.get("artificial_sweeteners", [])
    violations      = hidden_sugar.get("violations", [])

    col1, col2, col3 = st.columns(3)
    col1.metric("🍬 Sugar Aliases Found", alias_count)
    col2.metric("⚠️ Sugar Splitting", "YES" if splitting.get("detected") else "NO")
    col3.metric("🚨 Violations", len(violations))

    if alias_count > 0:
        st.markdown(f"""
        <div class="sugar-card">
            <span class="tag-sugar">SUGAR ALIASES</span><br/>
            <span style="font-size:0.85rem;opacity:0.8;">
                Found: {', '.join(aliases_found[:8])}{'...' if len(aliases_found) > 8 else ''}
            </span>
        </div>
        """, unsafe_allow_html=True)

    if splitting.get("detected"):
        st.markdown(f"""
        <div class="sugar-card">
            <span class="tag-sugar">SUGAR SPLITTING DETECTED</span><br/>
            <span style="font-size:0.85rem;opacity:0.8;">{splitting.get('message','')}</span>
        </div>
        """, unsafe_allow_html=True)

    if position.get("detected"):
        st.markdown(f"""
        <div class="violation-card">
            🚨 <strong>Sugar in Top 3 Ingredients</strong><br/>
            <span style="font-size:0.85rem;opacity:0.8;">{position.get('message','')}</span>
        </div>
        """, unsafe_allow_html=True)

    if high_gi:
        st.markdown(f"""
        <div class="sugar-card">
            <span class="tag-sugar">HIGH GI INGREDIENTS</span><br/>
            <span style="font-size:0.85rem;opacity:0.8;">{', '.join(high_gi)}</span>
        </div>
        """, unsafe_allow_html=True)

    if sweeteners:
        for sw in sweeteners:
            sev = sw.get("severity", "INFO")
            card = "violation-card" if sev == "HIGH" else "layer-card"
            st.markdown(f"""
            <div class="{card}">
                <strong>{sw.get('type','').replace('_',' ')}</strong><br/>
                <span style="font-size:0.85rem;opacity:0.8;">{sw.get('message','')}</span>
            </div>
            """, unsafe_allow_html=True)

    if violations:
        st.markdown("**Violations:**")
        for v in violations:
            sev_color = {"CRITICAL": "#ff0000", "HIGH": "#ff4400", "MEDIUM": "#ffaa00"}.get(
                v.get("severity"), "#ffaa00"
            )
            st.markdown(f"""
            <div class="violation-card">
                <span style="color:{sev_color};font-size:0.75rem;font-family:'DM Mono',monospace;">
                    {v.get('severity','')} · {v.get('type','')}
                </span><br/>
                {v.get('message','')}
            </div>
            """, unsafe_allow_html=True)

    if alias_count == 0 and not violations:
        st.success("✅ No hidden sugar patterns detected.")


def render_math(math_val: dict):
    failures = math_val.get("failures", [])
    if not failures:
        st.success("✅ All arithmetic checks passed. Calorie math is consistent.")
        return

    for f in failures:
        sev_color = {"CRITICAL": "#ff0000", "HIGH": "#ff4400", "MEDIUM": "#ffaa00"}.get(
            f.get("severity"), "#ffaa00"
        )
        st.markdown(f"""
        <div class="violation-card">
            <span style="color:{sev_color};font-family:'DM Mono',monospace;font-size:0.75rem;">
                {f.get('severity','?')} · {f.get('check','')}
            </span>
            <br/><strong>{f.get('message','')}</strong>
            <br/><span style="font-size:0.8rem;opacity:0.6;">
                Error: {f.get('error_pct',0):.1f}% &nbsp;·&nbsp; Section: {f.get('section','')}
            </span>
        </div>
        """, unsafe_allow_html=True)


def render_pdf_section(result: dict, final_report: dict):
    st.markdown("### 📄 Generate FSSAI Complaint")

    fraud_score = result.get("fraud_score", {})
    score = fraud_score.get("score", 0)

    if score <= 20:
        st.info("ℹ️ Fraud score is too low to generate a complaint. Product appears mostly clean.")
        return

    tier_info = {
        "advisory":  ("21-39", "Consumer Advisory",         "#ffaa00"),
        "complaint": ("40-69", "Formal FSSAI Complaint",    "#ff4400"),
        "urgent":    ("70+",   "Urgent FSSAI Complaint",    "#ff0000"),
    }
    tier = "urgent" if score >= 70 else ("complaint" if score >= 40 else "advisory")
    score_range, tier_label, tier_color = tier_info[tier]

    st.markdown(f"""
    <div class="pdf-box">
        <span style="color:{tier_color};font-family:'DM Mono',monospace;font-size:0.8rem;">
            SCORE {score} → {tier_label.upper()} ({score_range})
        </span><br/>
        <span style="font-size:0.9rem;opacity:0.8;">
            Fill in your details below to generate the complaint PDF.
        </span>
    </div>
    """, unsafe_allow_html=True)

    with st.form("complaint_form"):
        col1, col2 = st.columns(2)
        with col1:
            name    = st.text_input("Your Name", placeholder="Full name")
            address = st.text_input("Your Address", placeholder="City, State")
            phone   = st.text_input("Phone Number", placeholder="10 digit number")
        with col2:
            store         = st.text_input("Purchased From", placeholder="Amazon / BigBasket / store name")
            purchase_date = st.text_input("Purchase Date", placeholder="DD Month YYYY")

        submitted = st.form_submit_button("📄 Generate Complaint PDF")

    if submitted:
        if not name:
            st.error("Please enter your name to generate the complaint.")
            return

        with st.spinner("Generating complaint PDF..."):
            final_report["fraud_score"] = fraud_score
            final_report["product_name"] = (
                final_report.get("product", {}).get("name") or "Unknown Product"
            )

            pdf_result = generate_complaint(
                report=final_report,
                user_info={
                    "name":          name,
                    "address":       address,
                    "phone":         phone,
                    "store":         store,
                    "purchase_date": purchase_date,
                    "date":          date.today().strftime("%d %B %Y"),
                }
            )

        if pdf_result.get("generated"):
            filepath = pdf_result.get("filepath")
            tier_out = pdf_result.get("tier", "").upper()
            st.success(f"✅ {tier_out} complaint generated successfully.")

            with open(filepath, "rb") as f:
                st.download_button(
                    label="⬇️ Download Complaint PDF",
                    data=f.read(),
                    file_name=pdf_result.get("filename"),
                    mime="application/pdf",
                )
        else:
            st.error(f"Could not generate PDF: {pdf_result.get('reason')}")


# ── Main App ──────────────────────────────────────────────────

st.markdown('<div class="hero-title">🛡️ NutriGuard AI</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Automated Food Label Fraud Detection · FSSAI 2020 · NutriScore 2024 · RAG · Hidden Sugar</div>', unsafe_allow_html=True)

# Upload Mode
mode = st.radio(
    "Upload Mode",
    ["Single Image", "Dual Image (Front + Back)", "Triple Image (Front + Nutrition + Ingredients)"],
    horizontal=True,
)

result = None

# ── Single Image ──────────────────────────────────────────────
if mode == "Single Image":
    uploaded = st.file_uploader(
        "Upload food label image",
        type=["jpg", "jpeg", "png", "webp"],
    )
    if uploaded:
        st.image(uploaded, caption="Uploaded Label", use_container_width=True)
        if st.button("🔍 Analyse Label"):
            with st.spinner("Analysing..."):
                result = asyncio.run(run_pipeline_single(uploaded.read(), uploaded.name))

# ── Dual Image ────────────────────────────────────────────────
elif mode == "Dual Image (Front + Back)":
    col1, col2 = st.columns(2)
    with col1:
        front_upload = st.file_uploader("Front Label (claims)", type=["jpg","jpeg","png","webp"], key="front")
        if front_upload:
            st.image(front_upload, caption="Front Label", use_container_width=True)
    with col2:
        back_upload = st.file_uploader("Back Label (nutrition table)", type=["jpg","jpeg","png","webp"], key="back")
        if back_upload:
            st.image(back_upload, caption="Back Label", use_container_width=True)

    if front_upload and back_upload:
        if st.button("🔍 Analyse Both Labels"):
            with st.spinner("Merging and analysing..."):
                result = asyncio.run(run_pipeline_dual(
                    front_upload.read(), front_upload.name,
                    back_upload.read(), back_upload.name,
                ))

# ── Triple Image ──────────────────────────────────────────────
elif mode == "Triple Image (Front + Nutrition + Ingredients)":
    col1, col2, col3 = st.columns(3)
    with col1:
        front_upload = st.file_uploader("Front Label (claims)", type=["jpg","jpeg","png","webp"], key="front_triple")
        if front_upload:
            st.image(front_upload, caption="Front Label", use_container_width=True)
    with col2:
        back_upload = st.file_uploader("Nutrition Label", type=["jpg","jpeg","png","webp"], key="nutrition_triple")
        if back_upload:
            st.image(back_upload, caption="Nutrition Label", use_container_width=True)
    with col3:
        ingredients_upload = st.file_uploader("Ingredients Label", type=["jpg","jpeg","png","webp"], key="ingredients_triple")
        if ingredients_upload:
            st.image(ingredients_upload, caption="Ingredients Label", use_container_width=True)

    if front_upload and back_upload and ingredients_upload:
        if st.button("🔍 Analyse All Three Labels"):
            with st.spinner("Merging and analysing all three labels..."):
                result = asyncio.run(run_pipeline_triple(
                    front_upload.read(), front_upload.name,
                    back_upload.read(), back_upload.name,
                    ingredients_upload.read(), ingredients_upload.name,
                ))

# ── Results ───────────────────────────────────────────────────
if result:
    final_report  = result.get("final_report", {})
    product       = final_report.get("product", {})
    fraud_score   = result.get("fraud_score", {})
    math_val      = result.get("math_validation_result", {})
    regulatory    = result.get("regulatory_result", {})
    rag_result    = result.get("rag_result", {})
    nutriscore    = result.get("nutriscore_result", {})
    ingredient    = result.get("ingredient_result", {})
    hidden_sugar  = result.get("hidden_sugar_result", {})

    st.divider()

    # Mode badge
    is_triple = result.get("extraction_result", {}).get("triple_image", False)
    is_dual   = result.get("extraction_result", {}).get("dual_image", False)
    img_mode  = "Triple Image" if is_triple else ("Dual Image" if is_dual else "Single Image")
    st.markdown(f'<span class="mode-badge">📸 {img_mode} Analysis</span>', unsafe_allow_html=True)

    # Product Header
    st.markdown(f"## {product.get('name', 'Unknown Product')}")
    col1, col2, col3, col4 = st.columns(4)
    col1.markdown(f"**Brand:** {product.get('brand','N/A')}")
    col2.markdown(f"**FSSAI:** `{product.get('fssai_license') or 'Not found'}`")
    col3.markdown(f"**Serving:** {product.get('serving_size_g','N/A')}g")
    col4.markdown(f"**Dual/Triple:** {'Yes' if is_dual or is_triple else 'No'}")

    st.divider()

    # Fraud Score + Tabs
    score_col, detail_col = st.columns([1, 2])

    with score_col:
        st.markdown("### Fraud Score")
        render_fraud_score(fraud_score)

    with detail_col:
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "⚖️ REGULATORY",
            "🍬 HIDDEN SUGAR",
            "🌿 NUTRISCORE",
            "🧪 INGREDIENTS",
            "📐 MATH",
            "📄 COMPLAINT PDF",
        ])
        with tab1:
            render_regulatory(regulatory, rag_result)
        with tab2:
            render_hidden_sugar(hidden_sugar)
        with tab3:
            render_nutriscore(nutriscore)
        with tab4:
            render_ingredients(ingredient)
        with tab5:
            render_math(math_val)
        with tab6:
            render_pdf_section(result, final_report)

    # Raw JSON
    with st.expander("📄 Raw JSON Report"):
        st.json(final_report)