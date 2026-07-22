import sqlite3
import pandas as pd
import random
from datetime import datetime, timedelta
from database.db import DATABASE
from ml.prediction import predict_transaction
from ml.risk_engine import calculate_risk

hist_df = pd.read_csv("dataset/historical_transactions.csv")
hist_records = hist_df.to_dict(orient="records")

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
start_date = datetime.now() - timedelta(days=90)

conn = sqlite3.connect(DATABASE)
cur = conn.cursor()
cur.execute("SELECT count(*) FROM transactions")
count = cur.fetchone()[0]
conn.close()

needed = 30050 - count
print(f"Current count: {count}, needed: {needed}")

batch = []
for i in range(needed):
    template = random.choice(hist_records)
    txn_id = f"TXN{500000 + i}"
    cust_id = f"CUST{random.randint(1000, 2500)}"
    card = f"4{random.randint(100, 999)}********{random.randint(1000, 9999)}"
    
    date_str = (start_date + timedelta(days=random.randint(0, 90))).strftime("%Y-%m-%d")
    time_str = f"{random.randint(0,23):02d}:{random.randint(0,59):02d}:{random.randint(0,59):02d}"
    
    # Amounts in Indian Rupees (₹)
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
    
    batch.append((
        txn_id, cust_id, card, int(template["Customer_Age"]), template["Gender"], amt,
        merchant, city, state, cntry, dev, card_p, cvv, intl,
        daily_cnt, prev_f, pred, prob, risk_sc, level, rec, status, reason,
        f"{date_str} {time_str}"
    ))

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
""", batch)
conn.commit()
conn.close()
print("Batch added successfully!")
