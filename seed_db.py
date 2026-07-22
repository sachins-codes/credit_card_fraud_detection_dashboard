import os
import sqlite3
import random
import pandas as pd
from datetime import datetime, timedelta

from credit_card_fraud_detection_dashboard.database.db import DATABASE, create_database, insert_prediction
from credit_card_fraud_detection_dashboard.ml.prediction import predict_transaction
from credit_card_fraud_detection_dashboard.ml.risk_engine import calculate_risk

DATASET_PATH = "dataset/historical_transactions.csv"

indian_cities = [
    ("Mumbai", "Maharashtra"),
    ("Bengaluru", "Karnataka"),
    ("Delhi", "Delhi"),
    ("Chennai", "Tamil Nadu"),
    ("Hyderabad", "Telangana"),
    ("Pune", "Maharashtra"),
    ("Kolkata", "West Bengal"),
    ("Ahmedabad", "Gujarat")
]

indian_merchants = [
    "Amazon India", "Flipkart", "Swiggy", "Zomato", "Paytm Mall",
    "MakeMyTrip", "Reliance Digital", "BigBasket", "Nykaa", "BookMyShow"
]

countries = ["India", "India", "India", "India", "United States", "United Kingdom", "United Arab Emirates"]


def seed_database():
    print("=" * 60)
    print("Step 1: Training Machine Learning Models...")
    print("=" * 60)
    os.system("venv\\Scripts\\python train_models.py")

    print("\n" + "=" * 60)
    print("Step 2: Reinitializing Database...")
    print("=" * 60)
    if os.path.exists(DATABASE):
        os.remove(DATABASE)
        print(f"Removed existing database at {DATABASE}")

    create_database()

    print("\n" + "=" * 60)
    print("Step 3: Seeding Indian Transactions...")
    print("=" * 60)

    start_date = datetime.now() - timedelta(days=90)
    df_hist = pd.read_csv(DATASET_PATH)
    hist_records = df_hist.to_dict(orient="records")

    total_target = 30000
    batch_records = []
    
    for i in range(total_target):
        template = random.choice(hist_records)
        txn_id = f"TXN{100000 + i}"
        cust_id = f"CUST{random.randint(1000, 2500)}"
        card_num = f"4{random.randint(100, 999)}********{random.randint(1000, 9999)}"
        
        date_str = (start_date + timedelta(days=random.randint(0, 90))).strftime("%Y-%m-%d")
        time_str = f"{random.randint(0,23):02d}:{random.randint(0,59):02d}:{random.randint(0,59):02d}"

        # Indian Rupee amounts
        amt = round(random.uniform(50000, 250000), 2) if random.random() < 0.15 else round(random.uniform(100, 15000), 2)
        daily_cnt = random.randint(1, 15)
        prev_f = random.randint(1, 4) if random.random() < 0.05 else 0
        cvv = "Yes" if random.random() < 0.98 else "No"
        card_p = "Yes" if random.random() < 0.6 else "No"
        intl = "No" if random.random() < 0.9 else "Yes"
        dev = random.choice(["Mobile", "Desktop", "Tablet"])
        cntry = random.choice(countries)
        
        city_info = random.choice(indian_cities)
        city = city_info[0]
        state = city_info[1] if cntry == "India" else "N/A"
        merchant = random.choice(indian_merchants)

        is_f = random.random() < 0.12
        pred = "Fraud" if is_f else "Genuine"
        prob = round(random.uniform(70, 98), 2) if is_f else round(random.uniform(2, 35), 2)
        risk_sc = round(prob + random.uniform(0, 10), 2)
        risk_sc = min(100, risk_sc)
        
        if risk_sc >= 90:
            level = "CRITICAL"
        elif risk_sc >= 70:
            level = "HIGH"
        elif risk_sc >= 40:
            level = "MEDIUM"
        else:
            level = "LOW"

        if level in ["CRITICAL", "HIGH"]:
            rec = "BLOCK CARD IMMEDIATELY"
            status = "Blocked"
        elif level == "MEDIUM":
            rec = "MANUAL FRAUD REVIEW"
            status = "Under Review"
        else:
            rec = "APPROVE TRANSACTION"
            status = "Approved"

        reason = "Extremely high transaction amount (INR ₹), International transaction flag" if is_f else "Standard transaction profile"

        batch_records.append((
            txn_id, cust_id, card_num, int(template["Customer_Age"]), template["Gender"], amt,
            merchant, city, state, cntry, dev, card_p, cvv, intl,
            daily_cnt, prev_f, pred, prob, risk_sc, level, rec, status, reason,
            f"{date_str} {time_str}"
        ))

        if len(batch_records) >= 5000:
            _bulk_insert(batch_records)
            batch_records = []
            print(f"Seeded {i+1} of {total_target} transactions...")

    if batch_records:
        _bulk_insert(batch_records)

    print("\n" + "=" * 60)
    print("Database seeding completed successfully!")
    print("Total Transactions in DB:", total_target)
    print("=" * 60)


def _bulk_insert(records):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.executemany("""
        INSERT INTO transactions(
            transaction_id, customer_id, card_number, customer_age, gender, amount,
            merchant_category, city, state, country, device_type, card_present,
            cvv_matched, international_transaction, daily_transaction_count,
            previous_fraud_count, prediction, probability, risk_score,
            risk_level, recommendation, status, fraud_reason, created_at
        )
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, records)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    seed_database()
