import pandas as pd
import numpy as np

def explain_transaction(data, probability=50.0):
    """
    Explainable AI (XAI) engine.
    Calculates feature contribution percentages for a given transaction.
    Returns a sorted list of dicts with feature names, contribution percentages, and risk categories.
    """
    amount = float(data.get("Amount", 0.0))
    daily_count = int(data.get("Daily_Transaction_Count", 1))
    prev_fraud = int(data.get("Previous_Fraud_Count", 0))
    cvv_matched = str(data.get("CVV_Matched", "Yes"))
    card_present = str(data.get("Card_Present", "Yes"))
    intl = str(data.get("International_Transaction", "No"))
    device = str(data.get("Device_Type", "Mobile"))

    raw_scores = {}

    # 1. Amount Impact Score
    if amount > 100000:
        raw_scores["Transaction Amount Spike"] = 40.0
    elif amount > 50000:
        raw_scores["High Transaction Value"] = 30.0
    elif amount > 10000:
        raw_scores["Above Average Amount"] = 20.0
    elif amount > 2000:
        raw_scores["Moderate Transaction Value"] = 10.0
    else:
        raw_scores["Baseline Amount"] = 5.0

    # 2. International & Geo Risk Score
    if intl == "Yes":
        raw_scores["International Geo Anomaly"] = 25.0

    # 3. Previous Fraud History Link
    if prev_fraud > 0:
        raw_scores["Prior Account Fraud History"] = min(30.0, prev_fraud * 10.0)

    # 4. Velocity / Daily Transaction Count
    if daily_count > 10:
        raw_scores["High Daily Velocity (>10)"] = 20.0
    elif daily_count > 5:
        raw_scores["Moderate Daily Velocity (>5)"] = 10.0

    # 5. CVV Verification Mismatch
    if cvv_matched == "No":
        raw_scores["CVV Mismatch Risk"] = 25.0

    # 6. Card Not Present (CNP)
    if card_present == "No" and amount > 5000:
        raw_scores["Card Not Present (High Value)"] = 15.0

    # Normalize scores so they sum up to 100%
    total_score = sum(raw_scores.values())
    if total_score == 0:
        return [{"feature": "Standard Transaction Baseline", "impact": 100.0, "category": "Normal"}]

    explanations = []
    for feature, score in raw_scores.items():
        impact_pct = round((score / total_score) * 100.0, 1)
        category = "Critical" if impact_pct >= 25 else ("Warning" if impact_pct >= 15 else "Info")
        explanations.append({
            "feature": feature,
            "impact": impact_pct,
            "category": category
        })

    # Sort descending by impact percentage
    explanations.sort(key=lambda x: x["impact"], reverse=True)
    return explanations
