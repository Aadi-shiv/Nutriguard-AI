import streamlit as st
import asyncio
import json
from pathlib import Path

st.set_page_config(
    page_title="NutriGuard AI",
    page_icon="🛡️",
    layout="wide"
)

st.title("🛡️ NutriGuard AI")
st.caption("Automated Nutritional Fraud Detection for Indian Food Labels")

# Sidebar — image upload mode
st.sidebar.header("Upload Label Images")
mode = st.sidebar.radio(
    "Image Mode",
    ["Single Image", "Front + Back", "Front + Nutrition + Ingredients"]
)

front_img = back_img = ingredients_img = single_img = None

if mode == "Single Image":
    single_img = st.sidebar.file_uploader("Upload Label Image", type=["jpg", "jpeg", "png"])
elif mode == "Front + Back":
    front_img = st.sidebar.file_uploader("Front Label", type=["jpg", "jpeg", "png"])
    back_img = st.sidebar.file_uploader("Back Label", type=["jpg", "jpeg", "png"])
else:
    front_img = st.sidebar.file_uploader("Front Label", type=["jpg", "jpeg", "png"])
    back_img = st.sidebar.file_uploader("Nutrition Table", type=["jpg", "jpeg", "png"])
    ingredients_img = st.sidebar.file_uploader("Ingredients Image", type=["jpg", "jpeg", "png"])

analyze_btn = st.sidebar.button("🔍 Analyze Product", type="primary")

if analyze_btn:
    from app.pipeline.graph import nutriguard_pipeline

    state = {"pipeline_metadata": {}}

    if mode == "Single Image" and single_img:
        state["image_bytes"] = single_img.read()
        state["image_filename"] = single_img.name
    elif mode == "Front + Back" and front_img and back_img:
        state["front_image_bytes"] = front_img.read()
        state["front_image_filename"] = front_img.name
        state["back_image_bytes"] = back_img.read()
        state["back_image_filename"] = back_img.name
    else:
        if front_img and back_img and ingredients_img:
            state["front_image_bytes"] = front_img.read()
            state["front_image_filename"] = front_img.name
            state["back_image_bytes"] = back_img.read()
            state["back_image_filename"] = back_img.name
            state["ingredients_image_bytes"] = ingredients_img.read()
            state["ingredients_image_filename"] = ingredients_img.name
        else:
            st.warning("Please upload all required images.")
            st.stop()

    with st.spinner("Analyzing label... (this takes ~10 seconds)"):
        result = asyncio.run(nutriguard_pipeline.ainvoke(state))

    report = result.get("final_report", {})
    fraud = result.get("fraud_score", {})
    score = fraud.get("score", 0)

    # ── Fraud Score Banner ──────────────────────────────────────
    color = "🔴" if score >= 70 else "🟠" if score >= 40 else "🟡" if score >= 15 else "🟢"
    st.header(f"{color} Fraud Score: {score}/100 — {fraud.get('level', '')}")
    st.info(fraud.get("interpretation", ""))

    # ── Product Info ────────────────────────────────────────────
    prod = report.get("product", {})
    col1, col2, col3 = st.columns(3)
    col1.metric("Product", prod.get("name", "Unknown"))
    col2.metric("Brand", prod.get("brand", "Unknown"))
    col3.metric("NutriScore", result.get("nutriscore_result", {}).get("grade", "?"))

    # ── Fraud Signals ───────────────────────────────────────────
    signals = fraud.get("signals", [])
    if signals:
        st.subheader("⚠️ Fraud Signals Detected")
        for sig in signals:
            with st.expander(f"{sig['source']} — {sig['points']} points"):
                st.write(sig["signal"])
                for detail in sig.get("details", []):
                    st.markdown(f"- {detail}")

    # ── Layer Results Tabs ──────────────────────────────────────
    tabs = st.tabs(["📐 Math", "⚖️ FSSAI", "🌿 NutriScore", "🧪 Ingredients", "🍬 Sugar"])

    with tabs[0]:
        math = result.get("math_validation_result", {})
        if math.get("failures"):
            for f in math["failures"]:
                st.error(f["message"])
        else:
            st.success("All math checks passed ✅")

    with tabs[1]:
        reg = result.get("regulatory_result", {})
        for v in reg.get("claim_verdicts", []):
            if v["verdict"] == "NON_COMPLIANT":
                st.error(f"❌ {v['claim']}: {v['reason']}")
            elif v["verdict"] == "COMPLIANT":
                st.success(f"✅ {v['claim']}")
            else:
                st.warning(f"⚠️ {v['claim']}: Unverifiable")

    with tabs[2]:
        ns = result.get("nutriscore_result", {})
        st.metric("Grade", ns.get("grade"))
        st.metric("Score", ns.get("score"))
        col1, col2 = st.columns(2)
        col1.metric("Negative Points (N)", ns.get("negative_points", {}).get("total"))
        col2.metric("Positive Points (P)", ns.get("positive_points", {}).get("total"))
        if ns.get("protein_rule_applied"):
            st.warning(ns.get("protein_rule_note"))

    with tabs[3]:
        ing = result.get("ingredient_result", {})
        if ing.get("violations"):
            for v in ing["violations"]:
                st.error(v["message"])
        high = ing.get("additives", {}).get("high_concern", [])
        if high:
            st.warning(f"High-concern additives: {', '.join(a['code'] for a in high)}")
        if not ing.get("violations") and not high:
            st.success("No ingredient violations found ✅")

    with tabs[4]:
        sugar = result.get("hidden_sugar_result", {})
        splitting = sugar.get("sugar_splitting", {})
        if splitting.get("detected"):
            st.warning(splitting.get("message"))
        for v in sugar.get("violations", []):
            st.error(v["message"])
        if not sugar.get("has_violations") and not splitting.get("detected"):
            st.success("No hidden sugar issues found ✅")

    # ── Raw JSON ────────────────────────────────────────────────
    with st.expander("📄 View Full Report JSON"):
        st.json(report)