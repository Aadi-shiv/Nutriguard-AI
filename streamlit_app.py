"""
NutriGuard AI - Streamlit Frontend
Fixes:
- WebP image support added back
- Image upload on main screen (not sidebar)
- PDF complaint report generation included
"""

import os
import asyncio
import nest_asyncio
import streamlit as st
from pathlib import Path

nest_asyncio.apply()

# ── Page config ───────────────────────────────────────────────
st.set_page_config(
    page_title="NutriGuard AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ───────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0 0.5rem 0;
    }
    .main-header h1 {
        font-size: 2.5rem;
        font-weight: 800;
        color: #1a1a2e;
    }
    .main-header p {
        color: #555;
        font-size: 1.05rem;
    }
    .upload-box {
        border: 2px dashed #c0c0c0;
        border-radius: 12px;
        padding: 2rem;
        text-align: center;
        background: #fafafa;
        margin-bottom: 1rem;
    }
    .fraud-score-box {
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        margin-bottom: 1rem;
        color: white;
        font-size: 1.2rem;
        font-weight: bold;
    }
    .score-clean    { background: linear-gradient(135deg,#27ae60,#2ecc71); }
    .score-low      { background: linear-gradient(135deg,#f39c12,#f1c40f); }
    .score-medium   { background: linear-gradient(135deg,#e67e22,#d35400); }
    .score-high     { background: linear-gradient(135deg,#c0392b,#922b21); }
    .layer-card {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.8rem;
        border-left: 4px solid #1a1a2e;
    }
    .stButton > button {
        width: 100%;
        background-color: #1a1a2e;
        color: white;
        font-size: 1.1rem;
        font-weight: 700;
        border-radius: 8px;
        padding: 0.7rem;
        border: none;
        margin-top: 0.5rem;
    }
    .stButton > button:hover {
        background-color: #2d2d5e;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🛡️ NutriGuard AI</h1>
    <p>Automated Nutritional Fraud Detection · Powered by Mathematical Verification + FSSAI Compliance</p>
</div>
""", unsafe_allow_html=True)

st.divider()

# ── How-to info ───────────────────────────────────────────────
with st.expander("ℹ️ How to use NutriGuard AI", expanded=False):
    st.markdown("""
    **Upload Mode Options:**
    - **Single Image** – Upload front + back of label as one image
    - **Dual Image** – Upload front label separately and back label separately
    - **Triple Image** – Front label, nutrition table, and ingredients list as three separate images

    **What we check:**
    - ✅ Mathematical calorie verification (Atwater formula)
    - ✅ FSSAI 2020 threshold compliance (17 rules)
    - ✅ NutriScore 2024 grade (A–E)
    - ✅ INS additive concern levels
    - ✅ Hidden sugar detection (50+ aliases)
    - ✅ Serving size manipulation
    - ✅ RAG-based regulatory analysis

    **Supported formats:** JPG, JPEG, PNG, WEBP
    """)

# ── Upload mode selector ──────────────────────────────────────
st.subheader("📸 Upload Product Label")

upload_mode = st.radio(
    "Select upload mode:",
    ["Single Image", "Dual Image (Front + Back)", "Triple Image (Front + Nutrition + Ingredients)"],
    horizontal=True,
)

# ── File uploaders on MAIN SCREEN ────────────────────────────
ALLOWED_TYPES = ["jpg", "jpeg", "png", "webp"]

front_bytes = back_bytes = ingredients_bytes = single_bytes = None

if upload_mode == "Single Image":
    uploaded = st.file_uploader(
        "Upload product label image",
        type=ALLOWED_TYPES,
        help="Upload a clear image of the product label (front + back visible)",
    )
    if uploaded:
        single_bytes = uploaded.read()
        st.image(single_bytes, caption="Uploaded Label", use_column_width=True)

elif upload_mode == "Dual Image (Front + Back)":
    col1, col2 = st.columns(2)
    with col1:
        f = st.file_uploader("📋 Front Label (claims)", type=ALLOWED_TYPES, key="front")
        if f:
            front_bytes = f.read()
            st.image(front_bytes, caption="Front Label", use_column_width=True)
    with col2:
        b = st.file_uploader("📊 Back Label (nutrition)", type=ALLOWED_TYPES, key="back")
        if b:
            back_bytes = b.read()
            st.image(back_bytes, caption="Back Label", use_column_width=True)

else:  # Triple
    col1, col2, col3 = st.columns(3)
    with col1:
        f = st.file_uploader("📋 Front Label", type=ALLOWED_TYPES, key="front3")
        if f:
            front_bytes = f.read()
            st.image(front_bytes, caption="Front", use_column_width=True)
    with col2:
        b = st.file_uploader("📊 Nutrition Table", type=ALLOWED_TYPES, key="back3")
        if b:
            back_bytes = b.read()
            st.image(back_bytes, caption="Nutrition", use_column_width=True)
    with col3:
        i = st.file_uploader("🥗 Ingredients", type=ALLOWED_TYPES, key="ing3")
        if i:
            ingredients_bytes = i.read()
            st.image(ingredients_bytes, caption="Ingredients", use_column_width=True)

# ── Consumer info for PDF complaint ───────────────────────────
with st.expander("👤 Consumer Info (for PDF Complaint Report)", expanded=False):
    c1, c2 = st.columns(2)
    with c1:
        consumer_name = st.text_input("Your Name", value="Consumer")
        consumer_phone = st.text_input("Phone Number", value="9999999999")
        consumer_store = st.text_input("Store/Platform", value="Amazon India")
    with c2:
        consumer_address = st.text_input("Address", value="India")
        consumer_date = st.text_input("Purchase Date", value="01 April 2026")

# ── Analyze button ────────────────────────────────────────────
has_image = (
    single_bytes is not None or
    front_bytes is not None or
    back_bytes is not None
)

analyze_btn = st.button("🔍 Analyze Product", disabled=not has_image)

if not has_image:
    st.info("⬆️ Upload at least one label image above to begin analysis.")

# ── Analysis ──────────────────────────────────────────────────
if analyze_btn and has_image:
    with st.spinner("🔬 Analyzing label... this may take 10–30 seconds"):
        try:
            # Set env vars from Streamlit secrets
            for key in ["GROQ_API_KEY", "APP_ENV", "APP_VERSION", "LOG_LEVEL",
                        "RATE_LIMIT_PER_MINUTE", "CHROMA_PERSIST_DIR",
                        "API_HOST", "API_PORT", "ANTHROPIC_API_KEY", "GEMINI_API_KEY"]:
                if key in st.secrets:
                    os.environ[key] = str(st.secrets[key])

            from app.pipeline.graph import nutriguard_pipeline

            # Build state
            state = {"pipeline_metadata": {}}

            if upload_mode == "Single Image" and single_bytes:
                state["image_bytes"] = single_bytes
                state["image_filename"] = "label.jpg"

            elif upload_mode == "Dual Image (Front + Back)":
                if front_bytes:
                    state["front_image_bytes"] = front_bytes
                    state["front_image_filename"] = "front.jpg"
                if back_bytes:
                    state["back_image_bytes"] = back_bytes
                    state["back_image_filename"] = "back.jpg"

            else:  # Triple
                if front_bytes:
                    state["front_image_bytes"] = front_bytes
                    state["front_image_filename"] = "front.jpg"
                if back_bytes:
                    state["back_image_bytes"] = back_bytes
                    state["back_image_filename"] = "nutrition.jpg"
                if ingredients_bytes:
                    state["ingredients_image_bytes"] = ingredients_bytes
                    state["ingredients_image_filename"] = "ingredients.jpg"

            # Run pipeline
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(nutriguard_pipeline.ainvoke(state))

            st.success("✅ Analysis complete!")
            st.session_state["result"] = result

        except Exception as e:
            st.error(f"❌ Analysis failed: {str(e)}")
            st.exception(e)

# ── Results ───────────────────────────────────────────────────
if "result" in st.session_state:
    result = st.session_state["result"]
    report = result.get("final_report", {})
    fraud = result.get("fraud_score", {})

    st.divider()
    st.header("📊 Analysis Results")

    # Product info
    product = report.get("product", {})
    st.subheader(f"🏷️ {product.get('name', 'Unknown Product')} — {product.get('brand', '')}")
    if product.get("fssai_license"):
        st.caption(f"FSSAI: {product['fssai_license']}")

    # Fraud score
    score = fraud.get("score", 0)
    level = fraud.get("level", "MINIMAL")
    interpretation = fraud.get("interpretation", "")

    score_class = (
        "score-clean" if score == 0 else
        "score-low" if score < 20 else
        "score-medium" if score < 50 else
        "score-high"
    )

    st.markdown(f"""
    <div class="fraud-score-box {score_class}">
        🎯 FRAUD SCORE: {score} / 100 &nbsp;|&nbsp; {level}<br>
        <span style="font-size:0.9rem;font-weight:normal;">{interpretation}</span>
    </div>
    """, unsafe_allow_html=True)

    # Fraud signals
    signals = fraud.get("signals", [])
    if signals:
        with st.expander("⚠️ Fraud Signals Detected", expanded=True):
            for sig in signals:
                pts = sig.get("points", 0)
                color = "🔴" if pts >= 20 else "🟠" if pts >= 10 else "🟡"
                st.markdown(f"{color} **[{sig.get('source','').upper()}]** {sig.get('signal','')} *(+{pts} pts)*")
                for detail in sig.get("details", [])[:2]:
                    st.caption(f"↳ {detail[:150]}")

    # Tabs for layer results
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📐 Math Check", "⚖️ FSSAI Compliance", "🌿 NutriScore", "🧪 Ingredients", "🍬 Hidden Sugar"
    ])

    layer = report.get("layer_results", {})

    with tab1:
        math = layer.get("math_validation", {})
        failures = math.get("failures", [])
        if not failures:
            st.success("✅ All mathematical checks passed!")
        else:
            for f in failures:
                sev = f.get("severity", "MEDIUM")
                icon = "🔴" if sev == "CRITICAL" else "🟠" if sev == "HIGH" else "🟡"
                st.markdown(f"{icon} **{f.get('check','')}** — {f.get('message','')}")

    with tab2:
        reg = layer.get("regulatory_compliance", {})
        verdicts = reg.get("claim_verdicts", [])
        if not verdicts:
            st.info("No claims found to verify.")
        for v in verdicts:
            verdict = v.get("verdict", "")
            claim = v.get("claim", "")
            icon = "✅" if verdict == "COMPLIANT" else "❌" if verdict == "NON_COMPLIANT" else "❓"
            st.markdown(f"{icon} **{claim}** — {v.get('reason','')[:120]}")
            if v.get("regulation"):
                st.caption(f"📜 {v['regulation']}")

    with tab3:
        ns = layer.get("nutriscore", {})
        grade = ns.get("grade", "UNKNOWN")
        score_val = ns.get("score")
        grade_emoji = {"A": "🟢", "B": "🟩", "C": "🟡", "D": "🟠", "E": "🔴"}.get(grade, "⚪")
        st.metric("NutriScore Grade", f"{grade_emoji} {grade}", delta=f"Score: {score_val}")

        neg = ns.get("negative_points", {})
        pos = ns.get("positive_points", {})
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Negative Points (unhealthy)**")
            for k, v in neg.get("breakdown", {}).items():
                st.write(f"• {k.replace('_',' ').title()}: {v} pts")
            st.write(f"**Total N = {neg.get('total', 0)}**")
        with c2:
            st.markdown("**Positive Points (healthy)**")
            for k, v in pos.get("breakdown", {}).items():
                st.write(f"• {k.replace('_',' ').title()}: {v} pts")
            st.write(f"**Total P = {pos.get('total', 0)}**")

        if ns.get("protein_rule_applied"):
            st.warning("⚠️ 2024 Rule Applied: Protein points set to 0 because N ≥ 11")

    with tab4:
        ing = layer.get("ingredient_analysis", {})
        if not ing.get("analysed"):
            st.info("Ingredients list not visible in uploaded image.")
        else:
            additives = ing.get("additives", {})
            high = additives.get("high_concern", [])
            med = additives.get("medium_concern", [])

            if high:
                st.error(f"🔴 {len(high)} HIGH concern additives found:")
                for a in high:
                    st.markdown(f"- **{a['code']}** ({a['name']}): {a['notes']}")
            if med:
                st.warning(f"🟠 {len(med)} MEDIUM concern additives:")
                for a in med:
                    st.markdown(f"- **{a['code']}** ({a['name']}): {a['notes']}")
            if not high and not med:
                st.success("✅ No high/medium concern additives found.")

            viol = ing.get("violations", [])
            if viol:
                st.error("**Claim-Ingredient Contradictions:**")
                for v in viol:
                    st.markdown(f"❌ {v.get('message','')}")

    with tab5:
        hs = layer.get("hidden_sugar", {})
        if not hs.get("analysed"):
            st.info("Ingredients list not visible. Cannot detect hidden sugars.")
        else:
            count = hs.get("sugar_alias_count", 0)
            splitting = hs.get("sugar_splitting", {})
            st.metric("Sugar Aliases Found", count)

            if splitting.get("detected"):
                sev = splitting.get("severity", "")
                icon = "🔴" if sev == "HIGH" else "🟠"
                st.markdown(f"{icon} **Sugar Splitting:** {splitting.get('message','')}")

            viol = hs.get("violations", [])
            for v in viol:
                sev = v.get("severity", "")
                icon = "🔴" if sev == "CRITICAL" else "🟠"
                st.markdown(f"{icon} {v.get('message','')}")

            if count == 0 and not viol:
                st.success("✅ No hidden sugar tricks detected.")

    # ── PDF Complaint Report ──────────────────────────────────
    st.divider()
    st.subheader("📄 FSSAI Complaint Report")

    if score <= 20:
        st.info(f"Fraud score is {score}/100 — product is mostly clean. No complaint report generated.")
    else:
        tier = "advisory" if score <= 39 else "complaint" if score <= 69 else "URGENT"
        st.markdown(f"**Report Tier:** `{tier.upper()}` — Score: {score}/100")

        gen_pdf = st.button("📥 Generate PDF Complaint Report")

        if gen_pdf:
            with st.spinner("Generating PDF..."):
                try:
                    from app.reports.complaint_generator import generate_complaint

                    full_report = dict(report)
                    full_report["fraud_score"] = fraud
                    full_report["product_name"] = product.get("name", "Unknown Product")

                    user_info = {
                        "name": consumer_name,
                        "address": consumer_address,
                        "phone": consumer_phone,
                        "store": consumer_store,
                        "purchase_date": consumer_date,
                    }

                    pdf_result = generate_complaint(report=full_report, user_info=user_info)

                    if pdf_result.get("generated") and pdf_result.get("filepath"):
                        pdf_path = pdf_result["filepath"]
                        if Path(pdf_path).exists():
                            with open(pdf_path, "rb") as f:
                                pdf_bytes = f.read()
                            st.download_button(
                                label=f"⬇️ Download {tier.upper()} Report PDF",
                                data=pdf_bytes,
                                file_name=pdf_result.get("filename", "nutriguard_report.pdf"),
                                mime="application/pdf",
                            )
                            st.success("✅ PDF generated successfully!")
                        else:
                            st.error("PDF file not found after generation.")
                    else:
                        st.info(pdf_result.get("reason", "PDF not generated."))

                except Exception as e:
                    st.error(f"PDF generation failed: {str(e)}")
                    st.exception(e)

    # ── Raw JSON ──────────────────────────────────────────────
    with st.expander("🔧 Raw JSON Report (for debugging)", expanded=False):
        st.json(report)