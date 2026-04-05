"""
app/data/fssai_regulations.py
Complete FSSAI regulation text for RAG indexing.
Source: FSSAI Labelling Regulations 2020, Schedule II, Codex Alimentarius
"""

FSSAI_REGULATIONS = [
    {
        "id": "fssai_2020_cholesterol_free",
        "source": "FSSAI Labelling Regulations 2020",
        "section": "Schedule II, Regulation 2.4.7",
        "text": """Cholesterol Free Claim: A food may be described as 'cholesterol free' only if it contains 
        less than 0.005g (5mg) of cholesterol per 100g AND saturated fat does not exceed 1.5g per 100g 
        AND trans fatty acids do not exceed 0.2g per 100g. Products claiming cholesterol free must meet 
        ALL three conditions simultaneously. Violation of the saturated fat condition while claiming 
        cholesterol free is a serious misrepresentation as saturated fat has greater impact on blood 
        cholesterol levels than dietary cholesterol itself.""",
        "claim_type": "cholesterol_free",
        "nutrients_checked": ["cholesterol", "saturated_fat_g", "trans_fat_g"],
        "thresholds": {"cholesterol_mg": 5, "saturated_fat_g": 1.5, "trans_fat_g": 0.2}
    },
    {
        "id": "fssai_2020_low_fat",
        "source": "FSSAI Labelling Regulations 2020",
        "section": "Schedule II, Regulation 2.4.1",
        "text": """Low Fat Claim: A food may claim 'low fat' only if total fat does not exceed 3g per 100g 
        for solids or 1.5g per 100ml for liquids. The claim 'reduced fat' requires at least 25% less fat 
        than the reference food. 'Fat free' requires less than 0.5g fat per 100g. Products with fat 
        content above these thresholds cannot use low fat, reduced fat, or light fat claims.""",
        "claim_type": "low_fat",
        "nutrients_checked": ["fat_g"],
        "thresholds": {"fat_g_per_100g": 3.0}
    },
    {
        "id": "fssai_2020_high_protein",
        "source": "FSSAI Labelling Regulations 2020",
        "section": "Schedule II, Regulation 2.4.5",
        "text": """High Protein Claim: A food may claim 'high protein' or 'rich in protein' or 'excellent 
        source of protein' only if protein content is at least 12g per 100g for solids, providing at least 
        20% of energy from protein. 'Source of protein' or 'contains protein' or 'good source of protein' 
        requires minimum 6g per 100g providing at least 12% of energy from protein. Protein quality 
        (PDCAAS score) should also be considered for complete protein claims.""",
        "claim_type": "high_protein",
        "nutrients_checked": ["protein_g"],
        "thresholds": {"high_protein_g_per_100g": 12.0, "source_of_protein_g_per_100g": 6.0}
    },
    {
        "id": "fssai_2020_no_added_sugar",
        "source": "FSSAI Labelling Regulations 2020",
        "section": "Schedule II, Regulation 2.4.3",
        "text": """No Added Sugar Claim: A food may claim 'no added sugar' or 'without added sugar' only 
        if no sugar or any other food stuff used for its sweetening properties has been added to the food. 
        The label must also carry the declaration 'contains naturally occurring sugars' if the food 
        contains natural sugars. This claim does not mean the product is sugar-free as natural sugars 
        may still be present. Products using sugar alcohols, honey, fruit juice concentrates, or any 
        sweetening agents cannot claim no added sugar.""",
        "claim_type": "no_added_sugar",
        "nutrients_checked": ["added_sugar_g"],
        "thresholds": {"added_sugar_g": 0}
    },
    {
        "id": "fssai_2020_sugar_free",
        "source": "FSSAI Labelling Regulations 2020",
        "section": "Schedule II, Regulation 2.4.3",
        "text": """Sugar Free Claim: A food may claim 'sugar free' only if it contains less than 0.5g of 
        sugars per 100g or per 100ml. This includes all forms of sugar — sucrose, fructose, glucose, 
        lactose, maltose. Products containing more than 0.5g total sugars per 100g cannot use the 
        sugar free claim regardless of whether sugars are naturally occurring or added.""",
        "claim_type": "sugar_free",
        "nutrients_checked": ["sugar_g"],
        "thresholds": {"sugar_g_per_100g": 0.5}
    },
    {
        "id": "fssai_2020_low_sodium",
        "source": "FSSAI Labelling Regulations 2020",
        "section": "Schedule II, Regulation 2.4.6",
        "text": """Low Sodium Claim: A food may claim 'low sodium' or 'low salt' only if sodium content 
        does not exceed 120mg per 100g for solids. 'Very low sodium' requires less than 40mg per 100g. 
        'Sodium free' or 'salt free' requires less than 5mg per 100g. 'Reduced sodium' requires at least 
        25% less sodium than the reference food. High sodium products above 600mg per 100g should carry 
        a high sodium warning.""",
        "claim_type": "low_sodium",
        "nutrients_checked": ["sodium_mg"],
        "thresholds": {"low_sodium_mg_per_100g": 120, "very_low_sodium_mg_per_100g": 40, "high_sodium_warning_mg_per_100g": 600}
    },
    {
        "id": "fssai_2020_zero_trans_fat",
        "source": "FSSAI Food Safety Standards (Prohibition and Restriction on Sales) Amendment 2020",
        "section": "Regulation 2.2",
        "text": """Zero Trans Fat / Trans Fat Free Claim: India has one of the strictest trans fat 
        regulations globally. Trans fatty acids in oils and fats must not exceed 2% as of 2020 and 
        will be reduced to 1% by 2022. For a product to claim 'zero trans fat' or 'trans fat free', 
        trans fatty acid content must not exceed 0.2g per 100g. This is stricter than USA (0.5g) and 
        EU (2g). Products using partially hydrogenated oils cannot claim zero trans fat. 
        DALDA, vanaspati, and bakery fats are high-risk categories.""",
        "claim_type": "zero_trans_fat",
        "nutrients_checked": ["trans_fat_g"],
        "thresholds": {"trans_fat_g_per_100g": 0.2}
    },
    {
        "id": "fssai_2020_high_fiber",
        "source": "FSSAI Labelling Regulations 2020",
        "section": "Schedule II, Regulation 2.4.4",
        "text": """High Fiber / Rich in Fiber Claim: A food may claim 'high fiber' or 'rich in fiber' or 
        'excellent source of fiber' only if dietary fiber content is at least 6g per 100g. 'Source of 
        fiber' or 'contains fiber' or 'good source of fiber' requires minimum 3g per 100g. Fiber must 
        be dietary fiber as defined — non-digestible carbohydrates and lignin that beneficially affect 
        human physiology. Added isolated fibers must have proven physiological benefit.""",
        "claim_type": "high_fiber",
        "nutrients_checked": ["fiber_g"],
        "thresholds": {"high_fiber_g_per_100g": 6.0, "source_of_fiber_g_per_100g": 3.0}
    },
    {
        "id": "fssai_2020_low_calorie",
        "source": "FSSAI Labelling Regulations 2020",
        "section": "Schedule II, Regulation 2.4.2",
        "text": """Low Calorie / Low Energy Claim: A food may claim 'low calorie' or 'low energy' only 
        if energy value does not exceed 40 kcal per 100g for solids or 20 kcal per 100ml for liquids. 
        'Reduced calorie' requires at least 25% less energy than the reference food. 'Calorie free' 
        requires less than 4 kcal per 100g. Products marketed for weight management must not make 
        misleading low calorie claims if actual calorie content is substantial. Guilt free and similar 
        wellness claims on products above 200 kcal per 100g are considered misleading.""",
        "claim_type": "low_calorie",
        "nutrients_checked": ["energy_kcal"],
        "thresholds": {"low_calorie_kcal_per_100g": 40, "misleading_wellness_kcal_per_100g": 200}
    },
    {
        "id": "fssai_2020_natural_claim",
        "source": "FSSAI Labelling Regulations 2020",
        "section": "Regulation 13, Misleading Claims",
        "text": """Natural Claim Regulation: The term 'natural' may only be used for single foods or 
        ingredients that have not been significantly processed. A product containing artificial colours, 
        artificial flavours, artificial preservatives, or synthetic additives cannot claim to be 
        'natural', 'all natural', 'pure', or 'clean'. Nature-identical flavours are NOT natural flavours. 
        INS 102, 110, 124, 129 are artificial colours and preclude natural claims. Products using 
        MSG (INS 621) or MSG derivatives (INS 627, 631, 635) cannot claim natural flavouring.""",
        "claim_type": "natural",
        "nutrients_checked": ["ingredients"],
        "thresholds": {}
    },
    {
        "id": "fssai_2020_serving_size",
        "source": "FSSAI Labelling Regulations 2020",
        "section": "Regulation 5, Nutrition Information",
        "text": """Serving Size Regulation: Serving sizes must reflect amounts commonly consumed and 
        must be realistic for the product category. Manufacturers cannot use unrealistically small 
        serving sizes to make nutritional values appear more favorable. If stated serving size is 
        less than 60% of the commonly consumed amount for that product category, it is considered 
        serving size manipulation. Nutrition information must be declared per 100g AND per serving. 
        Miniaturized servings designed to hide nutrient levels through rounding are prohibited.""",
        "claim_type": "serving_size",
        "nutrients_checked": ["serving_size_g"],
        "thresholds": {}
    },
    {
        "id": "fssai_2020_calorie_calculation",
        "source": "FSSAI Labelling Regulations 2020",
        "section": "Regulation 5.1, Energy Calculation",
        "text": """Calorie Calculation Standard: Energy values on food labels must be calculated using 
        Atwater conversion factors: Protein = 4 kcal/g, Carbohydrates = 4 kcal/g, Fat = 9 kcal/g, 
        Dietary Fiber = 2 kcal/g (indigestible), Alcohol = 7 kcal/g, Organic acids = 3 kcal/g, 
        Polyols = 2.4 kcal/g. Stated calorie values must not deviate more than 10% from calculated 
        values. Systematic understatement of calories is considered nutritional fraud. Products 
        consistently understating calories across both per-serving and per-100g declarations are 
        particularly suspect.""",
        "claim_type": "calorie_accuracy",
        "nutrients_checked": ["energy_kcal", "protein_g", "carbohydrate_g", "fat_g", "fiber_g"],
        "thresholds": {"max_deviation_pct": 10}
    },
    {
        "id": "fssai_2020_misleading_claims",
        "source": "FSSAI Labelling Regulations 2020",
        "section": "Regulation 13, Prohibition of Misleading Claims",
        "text": """Prohibition of Misleading Claims: No food label shall contain any statement, claim, 
        design, device, or representation which is false or misleading or which is likely to create 
        a wrong impression regarding its character, value, quantity, composition, merit or safety. 
        Prohibited misleading tactics include: health halos on nutritionally poor products, use of 
        health-associated imagery (hearts, green leaves) on high fat/sugar/sodium products, wellness 
        language (guilt free, clean eating, superfood) without nutritional basis, and portion size 
        manipulation. Penalties under FSS Act 2006 range from ₹1 lakh to ₹10 lakh for misleading claims.""",
        "claim_type": "misleading",
        "nutrients_checked": [],
        "thresholds": {}
    },
    {
        "id": "fssai_2020_front_of_pack",
        "source": "FSSAI Draft Front of Pack Labelling Regulations 2022",
        "section": "Regulation 4, High Fat Sugar Salt Warning",
        "text": """Front of Pack Nutrition Labelling: Products must display high fat, high sugar, and 
        high sodium warnings on the front of pack if they exceed threshold levels. High fat threshold: 
        more than 20g per 100g total fat. High saturated fat threshold: more than 5g per 100g. 
        High sugar threshold: more than 22.5g per 100g total sugars. High sodium threshold: more than 
        600mg per 100g. Products triggering these thresholds while carrying positive health claims 
        (protein, fiber, vitamins) are considered to be creating misleading health halos.""",
        "claim_type": "front_of_pack_warning",
        "nutrients_checked": ["fat_g", "saturated_fat_g", "sugar_g", "sodium_mg"],
        "thresholds": {"high_fat_g": 20, "high_sat_fat_g": 5, "high_sugar_g": 22.5, "high_sodium_mg": 600}
    },
    {
        "id": "fssai_2020_organic_claim",
        "source": "FSSAI Organic Food Regulations 2017",
        "section": "Regulation 3",
        "text": """Organic Claim: Products claiming organic must be certified by APEDA or accredited 
        certification bodies under National Programme for Organic Production (NPOP) or Participatory 
        Guarantee System for India (PGS-India). The India Organic logo must be displayed. Products 
        cannot claim organic without valid certification. Partially organic products must specify 
        percentage of organic ingredients. Artificial additives, synthetic pesticides, or GMO 
        ingredients preclude organic certification.""",
        "claim_type": "organic",
        "nutrients_checked": [],
        "thresholds": {}
    },
    {
        "id": "codex_2021_nutrition_claims",
        "source": "Codex Alimentarius CAC/GL 23-1997 (Revised 2021)",
        "section": "Section 3, Nutrient Content Claims",
        "text": """Codex Guidelines for Nutrition Claims: Nutrient content claims should only be made 
        for nutrients for which recommended nutrient intakes have been established. Claims should be 
        based on the amount of the nutrient in a reasonable quantity of the food as consumed. 
        Comparative claims must specify the reference food and percentage difference. The claim 
        'light' or 'lite' must specify what property makes the food light. Energy claims must be 
        per 100g or per serving. All nutrient claims must be supported by the nutrition information 
        panel values.""",
        "claim_type": "general_nutrition",
        "nutrients_checked": [],
        "thresholds": {}
    },
    {
        "id": "fssai_2020_fortification",
        "source": "FSSAI Food Fortification Regulations 2018",
        "section": "Regulation 4",
        "text": """Fortification Claims: Products fortified with vitamins and minerals must meet minimum 
        fortification levels specified in Schedule I. The FSSAI + F logo (blue fortification logo) can 
        only be used on products meeting mandatory fortification standards. Claims like 'rich in 
        vitamins', 'fortified with iron', 'added calcium' must reflect actual fortification levels 
        meeting at least 15% of RDA per serving for 'source of' claims and 30% of RDA for 'rich in' 
        or 'high in' claims. Fortification claims on junk food are prohibited.""",
        "claim_type": "fortification",
        "nutrients_checked": ["calcium_mg", "iron_mg"],
        "thresholds": {"source_of_pct_rda": 15, "rich_in_pct_rda": 30}
    },
    {
        "id": "fssai_2020_gluten_free",
        "source": "FSSAI Labelling Regulations 2020",
        "section": "Schedule II, Regulation 2.4.9",
        "text": """Gluten Free Claim: A food may claim 'gluten free' only if it contains less than 
        20mg/kg (20 ppm) of gluten. This applies to all gluten sources including wheat, rye, barley, 
        oats, and their crossbred varieties. Products made from naturally gluten-free ingredients 
        in a facility that also processes gluten-containing foods must test below 20 ppm. 
        'Low gluten' claims require less than 100 ppm. Products claiming gluten free must have 
        testing documentation available.""",
        "claim_type": "gluten_free",
        "nutrients_checked": ["ingredients"],
        "thresholds": {"gluten_ppm": 20}
    },
    {
        "id": "fssai_2020_diabetic_claim",
        "source": "FSSAI Labelling Regulations 2020",
        "section": "Regulation 14, Special Dietary Foods",
        "text": """Diabetic/Sugar Suitable Claims: Products marketed as 'suitable for diabetics' or 
        'diabetic friendly' must have reduced glycemic impact. Such products must not contain added 
        sugars and must use only permitted sweeteners. High glycemic index ingredients like white 
        rice flour, maida, corn starch as primary ingredients preclude diabetic suitable claims. 
        Products must declare glycemic index if making glycemic claims. Total carbohydrate content 
        must be declared separately from dietary fiber and sugars.""",
        "claim_type": "diabetic_suitable",
        "nutrients_checked": ["sugar_g", "added_sugar_g", "carbohydrate_g"],
        "thresholds": {}
    },
    {
        "id": "fssai_2020_vegan_vegetarian",
        "source": "FSSAI Labelling Regulations 2020",
        "section": "Regulation 2.2.2, Green and Brown Dot",
        "text": """Vegetarian and Vegan Claims: All packaged foods must display a green dot (vegetarian) 
        or brown dot (non-vegetarian) symbol prominently. Vegetarian products must not contain any 
        meat, poultry, seafood, eggs, or animal-derived ingredients including gelatin, rennet, 
        cochineal (INS 120), and certain food additives derived from animals. INS 631 (disodium 
        inosinate) and INS 627 (disodium guanylate) may be derived from meat or fish and preclude 
        vegetarian claims unless specifically plant-derived. Vegan claims additionally exclude 
        all dairy and honey.""",
        "claim_type": "vegetarian_vegan",
        "nutrients_checked": ["ingredients"],
        "thresholds": {}
    },
    {
        "id": "fssai_2020_infant_food",
        "source": "FSSAI Infant Milk Substitutes Regulations 2011 (Amended 2020)",
        "section": "Regulation 7",
        "text": """Infant and Baby Food Claims: Foods for infants and young children have the strictest 
        labelling requirements. No promotional material or health claims are permitted on infant formula. 
        Products for children under 3 years cannot contain artificial colours, artificial flavours, 
        added sugars exceeding 10g per 100g, sodium exceeding 200mg per 100g, or saturated fat 
        exceeding 10% of total energy. High sugar, high fat, or high sodium products marketed 
        towards children through child-appealing packaging violate FSSAI guidelines.""",
        "claim_type": "infant_child_food",
        "nutrients_checked": ["sugar_g", "sodium_mg", "saturated_fat_g"],
        "thresholds": {}
    }
]