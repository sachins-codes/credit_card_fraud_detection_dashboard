import os
import json
import sqlite3
import pandas as pd
from io import BytesIO, StringIO
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
    send_file
)

from credit_card_fraud_detection_dashboard.database.db import (
    create_database,
    dashboard_counts,
    get_recent_transactions,
    get_paginated_transactions,
    get_transaction_by_id,
    get_customer_history,
    get_analytics_data,
    insert_prediction,
    get_all_rules,
    insert_rule,
    delete_rule,
    toggle_rule,
    get_geo_fraud_points
)

from credit_card_fraud_detection_dashboard.ml.prediction import predict_transaction
from credit_card_fraud_detection_dashboard.ml.risk_engine import calculate_risk
from credit_card_fraud_detection_dashboard.ml.xai_engine import explain_transaction

app = Flask(__name__)
app.secret_key = "creditcardfraud_industry_level_secret_key"

create_database()


def get_model_accuracies():
    accuracy_file = "models/model_accuracies.json"
    if os.path.exists(accuracy_file):
        try:
            with open(accuracy_file, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "decision_tree": 98.50,
        "logistic_regression": 95.20,
        "random_forest": 99.10,
        "isolation_forest": 96.50
    }


# ------------------------
# Login & Logout
# ------------------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == "admin" and password == "admin123":
            session["user"] = username
            flash("Welcome back, Security Administrator!")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials. Try admin / admin123")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.")
    return redirect(url_for("login"))


# ------------------------
# Dashboard
# ------------------------
@app.route("/dashboard")
def dashboard():
    counts = dashboard_counts()
    recent = get_recent_transactions(10)
    accuracies = get_model_accuracies()
    
    return render_template(
        "dashboard.html",
        counts=counts,
        recent=recent,
        accuracies=accuracies,
        active_page="dashboard"
    )


# ------------------------
# Fraud IDs Page
# ------------------------
@app.route("/fraudids")
def fraudids():
    search_query = request.args.get("search", "").strip()
    risk_level = request.args.get("risk_level", "").strip()
    status = request.args.get("status", "").strip()
    device_type = request.args.get("device_type", "").strip()
    min_amount = request.args.get("min_amount", "").strip()
    max_amount = request.args.get("max_amount", "").strip()

    filters = {
        "risk_level": risk_level,
        "status": status,
        "device_type": device_type,
        "min_amount": min_amount,
        "max_amount": max_amount
    }

    try:
        limit = int(request.args.get("limit", 10))
    except ValueError:
        limit = 10

    try:
        page = int(request.args.get("page", 1))
    except ValueError:
        page = 1

    if page < 1:
        page = 1

    offset = (page - 1) * limit

    transactions, total_count = get_paginated_transactions(
        limit=limit,
        offset=offset,
        search_query=search_query,
        filters=filters,
        fraud_only=True
    )

    total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1

    return render_template(
        "fraudids.html",
        transactions=transactions,
        total_count=total_count,
        page=page,
        limit=limit,
        offset=offset,
        total_pages=total_pages,
        search_query=search_query,
        filters=filters,
        active_page="fraudids"
    )


# ------------------------
# All Transaction History Page
# ------------------------
@app.route("/history")
def history():
    search_query = request.args.get("search", "").strip()
    risk_level = request.args.get("risk_level", "").strip()
    status = request.args.get("status", "").strip()
    device_type = request.args.get("device_type", "").strip()
    min_amount = request.args.get("min_amount", "").strip()
    max_amount = request.args.get("max_amount", "").strip()

    filters = {
        "risk_level": risk_level,
        "status": status,
        "device_type": device_type,
        "min_amount": min_amount,
        "max_amount": max_amount
    }

    try:
        limit = int(request.args.get("limit", 10))
    except ValueError:
        limit = 10

    try:
        page = int(request.args.get("page", 1))
    except ValueError:
        page = 1

    if page < 1:
        page = 1

    offset = (page - 1) * limit

    transactions, total_count = get_paginated_transactions(
        limit=limit,
        offset=offset,
        search_query=search_query,
        filters=filters,
        fraud_only=False
    )

    total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1

    return render_template(
        "history.html",
        transactions=transactions,
        total_count=total_count,
        page=page,
        limit=limit,
        offset=offset,
        total_pages=total_pages,
        search_query=search_query,
        filters=filters,
        active_page="history"
    )


# ------------------------
# Fraud Investigation Page
# ------------------------
@app.route("/investigate/<transaction_id>")
def investigate(transaction_id):
    txn = get_transaction_by_id(transaction_id)
    if not txn:
        flash(f"Transaction ID '{transaction_id}' not found.")
        return redirect(url_for("fraudids"))

    customer_history = get_customer_history(txn["customer_id"], current_txn_id=transaction_id)
    xai_factors = explain_transaction(txn, probability=txn.get("probability", 50.0))

    return render_template(
        "investigation.html",
        txn=txn,
        customer_history=customer_history,
        xai_factors=xai_factors,
        active_page="fraudids"
    )


# ------------------------
# Policy Rules Page
# ------------------------
@app.route("/rules", methods=["GET", "POST"])
def rules():
    if request.method == "POST":
        rule_name = request.form.get("rule_name")
        field = request.form.get("condition_field")
        op = request.form.get("condition_operator")
        val = request.form.get("condition_value")
        action = request.form.get("action")
        try:
            insert_rule(rule_name, field, op, val, action)
            flash(f"Security policy '{rule_name}' deployed successfully.")
        except Exception as e:
            flash(f"Error deploying policy: {e}")
        return redirect(url_for("rules"))

    active_rules = get_all_rules()
    return render_template("rules.html", rules=active_rules, active_page="rules")


@app.route("/toggle_rule/<int:rule_id>")
def toggle_rule_route(rule_id):
    toggle_rule(rule_id)
    flash("Policy status updated.")
    return redirect(url_for("rules"))


@app.route("/delete_rule/<int:rule_id>")
def delete_rule_route(rule_id):
    delete_rule(rule_id)
    flash("Policy deleted.")
    return redirect(url_for("rules"))


# ------------------------
# Reports Analytics Page
# ------------------------
@app.route("/reports")
def reports():
    return render_template("reports.html", active_page="reports")


# ------------------------
# API Endpoints
# ------------------------
@app.route("/api/analytics")
def api_analytics():
    analytics = get_analytics_data()
    counts = dashboard_counts()
    accuracies = get_model_accuracies()

    analytics["counts"] = counts
    analytics["accuracies"] = accuracies

    return jsonify(analytics)


@app.route("/api/geo_fraud")
def api_geo_fraud():
    points = get_geo_fraud_points()
    return jsonify(points)


# ------------------------
# New Transaction Simulator
# ------------------------
@app.route("/new_transaction", methods=["GET", "POST"])
@app.route("/prediction", methods=["GET", "POST"])
def new_transaction():
    if request.method == "POST":
        import random
        from datetime import datetime

        cust_id = request.form.get("customer_id", f"CUST{random.randint(1000, 9999)}")
        card_num = request.form.get("card_number", "4111222233334444")
        amount = float(request.form.get("amount", 100.0))
        cust_age = int(request.form.get("customer_age", 35))
        gender = request.form.get("gender", "M")
        merchant_cat = request.form.get("merchant_category", "Retail")
        city = request.form.get("city", "New York")
        state = request.form.get("state", "NY")
        country = request.form.get("country", "United States")
        device_type = request.form.get("device_type", "Mobile")
        card_present = request.form.get("card_present", "Yes")
        cvv_matched = request.form.get("cvv_matched", "Yes")
        international = request.form.get("international_transaction", "No")
        daily_count = int(request.form.get("daily_transaction_count", 1))
        prev_fraud = int(request.form.get("previous_fraud_count", 0))

        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")

        txn_id = f"TXN{random.randint(300000, 999999)}"

        data_input = {
            "Transaction_ID": txn_id,
            "Customer_ID": cust_id,
            "Card_Number": card_num,
            "Customer_Age": cust_age,
            "Gender": gender,
            "Merchant_Category": merchant_cat,
            "Amount": amount,
            "Transaction_Date": date_str,
            "Transaction_Time": time_str,
            "City": city,
            "State": state,
            "Country": country,
            "Device_Type": device_type,
            "Card_Present": card_present,
            "CVV_Matched": cvv_matched,
            "International_Transaction": international,
            "Daily_Transaction_Count": daily_count,
            "Previous_Fraud_Count": prev_fraud
        }

        # Run 4-model ensemble prediction
        pred_res = predict_transaction(data_input)

        # Run Risk Evaluation engine
        risk_res = calculate_risk(
            probability=pred_res["Probability"],
            amount=amount,
            international=international,
            previous_fraud=prev_fraud,
            daily_transactions=daily_count,
            cvv_matched=cvv_matched,
            card_present=card_present
        )

        record = {
            "transaction_id": txn_id,
            "customer_id": cust_id,
            "card_number": card_num,
            "customer_age": cust_age,
            "gender": gender,
            "amount": amount,
            "merchant_category": merchant_cat,
            "city": city,
            "state": state,
            "country": country,
            "device_type": device_type,
            "card_present": card_present,
            "cvv_matched": cvv_matched,
            "international_transaction": international,
            "daily_transaction_count": daily_count,
            "previous_fraud_count": prev_fraud,
            "prediction": pred_res["Prediction"],
            "probability": pred_res["Probability"],
            "risk_score": risk_res["Risk Score"],
            "risk_level": risk_res["Risk Level"],
            "recommendation": risk_res["Recommendation"],
            "status": risk_res["Status"],
            "fraud_reason": risk_res["Fraud Reason"],
            "created_at": f"{date_str} {time_str}"
        }

        insert_prediction(record)

        flash(f"Transaction {txn_id} processed: Predicted as {pred_res['Prediction']} (Risk: {risk_res['Risk Level']})")
        return redirect(url_for("investigate", transaction_id=txn_id))

    return render_template("new_transaction.html", active_page="new_transaction")


# ------------------------
# Export Handlers
# ------------------------
@app.route("/export")
@app.route("/export_fraud_csv")
def export_data():
    export_format = request.args.get("format", "csv").lower()
    export_type = request.args.get("type", "fraud").lower()

    search_query = request.args.get("search", "").strip()
    risk_level = request.args.get("risk_level", "").strip()
    status = request.args.get("status", "").strip()
    device_type = request.args.get("device_type", "").strip()
    min_amount = request.args.get("min_amount", "").strip()
    max_amount = request.args.get("max_amount", "").strip()

    filters = {
        "risk_level": risk_level,
        "status": status,
        "device_type": device_type,
        "min_amount": min_amount,
        "max_amount": max_amount
    }

    rows, _ = get_paginated_transactions(
        limit=100000,
        offset=0,
        search_query=search_query,
        filters=filters,
        fraud_only=(export_type == "fraud")
    )

    if not rows:
        flash("No transactions available for export with current filters.")
        return redirect(url_for("fraudids" if export_type == "fraud" else "history"))

    df = pd.DataFrame(rows)
    filename_base = f"Fraud_Report_{export_type}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}"

    if export_format == "excel":
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Transactions")
        output.seek(0)
        return send_file(
            output,
            as_attachment=True,
            download_name=f"{filename_base}.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        output = BytesIO()
        df.to_csv(output, index=False)
        output.seek(0)
        return send_file(
            output,
            as_attachment=True,
            download_name=f"{filename_base}.csv",
            mimetype="text/csv"
        )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)