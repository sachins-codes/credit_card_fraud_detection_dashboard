import pandas as pd
import joblib
import os

# Lazy loading placeholders
dt_model = None
lr_model = None
rf_model = None
iso_model = None
encoders = None
scaler = None


def load_resources():
    global dt_model, lr_model, rf_model, iso_model, encoders, scaler
    if dt_model is None:
        dt_model = joblib.load("models/decision_tree.pkl")
        lr_model = joblib.load("models/logistic.pkl")
        rf_model = joblib.load("models/random_forest.pkl")
        if os.path.exists("models/isolation_forest.pkl"):
            iso_model = joblib.load("models/isolation_forest.pkl")
        encoders = joblib.load("models/label_encoders.pkl")
        scaler = joblib.load("models/scaler.pkl")


def predict_transaction(data):
    load_resources()

    # Convert dictionary into DataFrame
    df = pd.DataFrame([data])

    # -----------------------------
    # Parse Date Features
    # -----------------------------
    if "Transaction_Date" in df.columns:
        df["Transaction_Date"] = pd.to_datetime(df["Transaction_Date"])
        df["Year"] = df["Transaction_Date"].dt.year
        df["Month"] = df["Transaction_Date"].dt.month
        df["Day"] = df["Transaction_Date"].dt.day
        df.drop(columns="Transaction_Date", inplace=True)
    else:
        from datetime import datetime
        now = datetime.now()
        df["Year"] = now.year
        df["Month"] = now.month
        df["Day"] = now.day

    # -----------------------------
    # Parse Time Features
    # -----------------------------
    if "Transaction_Time" in df.columns:
        df["Hour"] = pd.to_datetime(df["Transaction_Time"], format="%H:%M:%S", errors="coerce").dt.hour
        if df["Hour"].isnull().any():
            df["Hour"] = pd.to_datetime(df["Transaction_Time"], errors="coerce").dt.hour
        df["Hour"] = df["Hour"].fillna(12).astype(int)
        df.drop(columns="Transaction_Time", inplace=True)
    else:
        df["Hour"] = 12

    # -----------------------------
    # Remove unwanted columns
    # -----------------------------
    drop_columns = ["Transaction_ID", "Customer_ID", "Card_Number"]
    for col in drop_columns:
        if col in df.columns:
            df.drop(columns=col, inplace=True)

    # -----------------------------
    # Encode categorical columns
    # -----------------------------
    categorical_columns = [
        "Gender",
        "Merchant_Category",
        "City",
        "State",
        "Country",
        "Device_Type",
        "Card_Present",
        "CVV_Matched",
        "International_Transaction"
    ]

    for column in categorical_columns:
        encoder = encoders[column]
        classes_set = set(encoder.classes_)
        df[column] = df[column].astype(str).apply(
            lambda x: x if x in classes_set else str(encoder.classes_[0])
        )
        df[column] = encoder.transform(df[column])

    # -----------------------------
    # Ensure Column Ordering Matches Training Features
    # -----------------------------
    features_order = [
        'Customer_Age', 'Gender', 'Merchant_Category', 'Amount', 'City',
        'State', 'Country', 'Device_Type', 'Card_Present', 'CVV_Matched',
        'International_Transaction', 'Daily_Transaction_Count',
        'Previous_Fraud_Count', 'Year', 'Month', 'Day', 'Hour'
    ]
    df = df[features_order]

    # -----------------------------
    # Apply Scaler
    # -----------------------------
    df_scaled = scaler.transform(df)

    # Supervised Predictions
    dt_pred = dt_model.predict(df_scaled)[0]
    lr_pred = lr_model.predict(df_scaled)[0]
    rf_pred = rf_model.predict(df_scaled)[0]

    dt_prob = dt_model.predict_proba(df_scaled)[0][1]
    lr_prob = lr_model.predict_proba(df_scaled)[0][1]
    rf_prob = rf_model.predict_proba(df_scaled)[0][1]

    # Unsupervised Anomaly Detection (Isolation Forest)
    iso_pred = 0
    iso_score = 0.0
    if iso_model is not None:
        raw_iso = iso_model.predict(df_scaled)[0]
        iso_pred = 1 if raw_iso == -1 else 0
        raw_dec = iso_model.decision_function(df_scaled)[0]
        iso_score = round(max(0.0, min(100.0, (0.5 - raw_dec) * 100.0)), 2)

    # Ensemble Weighted Probability (DT 25%, LR 25%, RF 35%, IsoForest 15%)
    final_probability = (
        dt_prob * 0.25 +
        lr_prob * 0.25 +
        rf_prob * 0.35 +
        (iso_score / 100.0) * 0.15
    )

    final_prediction = 1 if final_probability >= 0.45 else 0

    return {
        "Decision Tree": int(dt_pred),
        "Logistic Regression": int(lr_pred),
        "Random Forest": int(rf_pred),
        "Isolation Forest": int(iso_pred),
        "DT_Prob": round(dt_prob * 100, 2),
        "LR_Prob": round(lr_prob * 100, 2),
        "RF_Prob": round(rf_prob * 100, 2),
        "ISO_Score": iso_score,
        "Probability": round(final_probability * 100, 2),
        "Prediction": "Fraud" if final_prediction else "Genuine"
    }