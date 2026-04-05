import asyncio
import json
from app.pipeline.graph import nutriguard_pipeline
from app.reports.complaint_generator import generate_complaint

async def test_dual(front_file: str, back_file: str, label: str):
    """Test with front + back images merged natively in pipeline."""
    print(f"\n{'='*60}")
    print(f"DUAL IMAGE TEST: {label}")
    print(f"Front: {front_file} | Back: {back_file}")
    print(f"{'='*60}")

    with open(f"tests/fixtures/sample_labels/{front_file}", "rb") as f:
        front_bytes = f.read()
    with open(f"tests/fixtures/sample_labels/{back_file}", "rb") as f:
        back_bytes = f.read()

    result = await nutriguard_pipeline.ainvoke({
        "front_image_bytes": front_bytes,
        "front_image_filename": front_file,
        "back_image_bytes": back_bytes,
        "back_image_filename": back_file,
        "pipeline_metadata": {},
    })
    

    print(f"\nPRODUCT: {result['final_report']['product']['name']}")
    print(f"DUAL IMAGE: {result['final_report']['product']['dual_image_analysis']}")

    print("\n=== REGULATORY COMPLIANCE ===")
    print(json.dumps(result["regulatory_result"], indent=2))

    print("\n=== INGREDIENT ANALYSIS ===")
    print(json.dumps(result["ingredient_result"], indent=2))

    print("\n=== NUTRISCORE 2024 ===")
    grade = result["nutriscore_result"]["grade"]
    score = result["nutriscore_result"]["score"]
    print(f"Grade: {grade} | Score: {score}")

    print("\n=== FINAL FRAUD SCORE ===")
    print(json.dumps(result["fraud_score"], indent=2))
    # Generate complaint PDF
    # Generate complaint PDF
    from app.reports.complaint_generator import generate_complaint
    final_report = result.get("final_report", {})
    final_report["fraud_score"] = result.get("fraud_score", {})
    final_report["product_name"] = final_report.get("product", {}).get("name") or "Cheesy Cheddar Makhana"
    pdf_result = generate_complaint(
        report=final_report,
        user_info={
            "name": "Test Consumer",
            "address": "Mumbai, Maharashtra",
            "phone": "9999999999",
            "store": "Amazon India",
            "purchase_date": "10 March 2026",
        }
    )
    print("\n=== COMPLAINT PDF ===")
    print(json.dumps(pdf_result, indent=2))
async def test_triple(front_file, back_file, ingredients_file, label):
    print(f"\n{'='*60}")
    print(f"TRIPLE IMAGE TEST: {label}")
    print(f"{'='*60}")

    with open(f"tests/fixtures/sample_labels/{front_file}", "rb") as f:
        front_bytes = f.read()
    with open(f"tests/fixtures/sample_labels/{back_file}", "rb") as f:
        back_bytes = f.read()
    with open(f"tests/fixtures/sample_labels/{ingredients_file}", "rb") as f:
        ingredients_bytes = f.read()

    result = await nutriguard_pipeline.ainvoke({
        "front_image_bytes": front_bytes,
        "front_image_filename": front_file,
        "back_image_bytes": back_bytes,
        "back_image_filename": back_file,
        "ingredients_image_bytes": ingredients_bytes,
        "ingredients_image_filename": ingredients_file,
        "pipeline_metadata": {},
    })    
if __name__ == "__main__":
    asyncio.run(test_dual("test_label2.jpeg", "test_label3.jpeg", "FARMLEY CHEESY CHEDDAR MAKHANA"))