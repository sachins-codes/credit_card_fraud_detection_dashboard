def calculate_risk(probability, amount,
                   international,
                   previous_fraud,
                   daily_transactions,
                   cvv_matched="Yes",
                   card_present="Yes"):

    score = probability

    # Amount
    if amount > 100000:
        score += 10
    elif amount > 50000:
        score += 5

    # International Transaction
    if international == "Yes":
        score += 10

    # Previous Fraud
    score += previous_fraud * 5

    # Daily Transactions
    if daily_transactions > 10:
        score += 5

    # Maximum Score
    if score > 100:
        score = 100

    # Compile Fraud Reasons
    reasons = []
    if probability >= 50:
        reasons.append("High ML prediction probability")
    if amount > 100000:
        reasons.append("Extremely high transaction amount")
    elif amount > 50000:
        reasons.append("Unusual high value transaction")
    if international == "Yes":
        reasons.append("International transaction flag")
    if previous_fraud > 0:
        reasons.append(f"Linked to previous fraud account ({previous_fraud} instances)")
    if daily_transactions > 10:
        reasons.append("Abnormally high daily transaction frequency")
    if cvv_matched == "No":
        reasons.append("CVV verification mismatch")

    if not reasons:
        if score >= 40:
            reasons.append("Suspicious behavioral metrics")
        else:
            reasons.append("Standard transaction profile")

    fraud_reason = ", ".join(reasons)

    # Risk Level & Recommendation mapping
    if score >= 90:
        risk = "CRITICAL"
        recommendation = "BLOCK CARD IMMEDIATELY"
        status = "Blocked"
    elif score >= 70:
        risk = "HIGH"
        recommendation = "HOLD & VERIFY CUSTOMER"
        status = "Blocked"
    elif score >= 40:
        risk = "MEDIUM"
        recommendation = "MANUAL FRAUD REVIEW"
        status = "Under Review"
    else:
        risk = "LOW"
        recommendation = "APPROVE TRANSACTION"
        status = "Approved"

    return {
        "Risk Score": round(score, 2),
        "Risk Level": risk,
        "Recommendation": recommendation,
        "Status": status,
        "Fraud Reason": fraud_reason
    }