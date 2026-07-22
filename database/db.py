import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE = os.path.join(BASE_DIR, "database", "database.db")

CITY_COORDINATES = {
    "Mumbai": [19.0760, 72.8777],
    "Bengaluru": [12.9716, 77.5946],
    "Delhi": [28.6139, 77.2090],
    "Chennai": [13.0827, 80.2707],
    "Hyderabad": [17.3850, 78.4867],
    "Pune": [18.5204, 73.8567],
    "Kolkata": [22.5726, 88.3639],
    "Ahmedabad": [23.0225, 72.5714],
    "New York": [40.7128, -74.0060],
    "London": [51.5074, -0.1278],
    "Tokyo": [35.6762, 139.6503],
    "Toronto": [43.6532, -79.3832]
}


def create_database():
    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id TEXT UNIQUE,
            customer_id TEXT,
            card_number TEXT,
            customer_age INTEGER,
            gender TEXT,
            amount REAL,
            merchant_category TEXT,
            city TEXT,
            state TEXT,
            country TEXT,
            device_type TEXT,
            card_present TEXT,
            cvv_matched TEXT,
            international_transaction TEXT,
            daily_transaction_count INTEGER,
            previous_fraud_count INTEGER,
            prediction TEXT,
            probability REAL,
            risk_score REAL,
            risk_level TEXT,
            recommendation TEXT,
            status TEXT,
            fraud_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rules(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_name TEXT UNIQUE,
            condition_field TEXT,
            condition_operator TEXT,
            condition_value TEXT,
            action TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_txn_id ON transactions(transaction_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_customer_id ON transactions(customer_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_prediction ON transactions(prediction)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_risk_level ON transactions(risk_level)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON transactions(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON transactions(created_at)")

    # Seed Default Security Rules if empty
    cursor.execute("SELECT COUNT(*) FROM rules")
    if cursor.fetchone()[0] == 0:
        default_rules = [
            ("Block High Value International", "amount", ">=", "50000", "BLOCK CARD"),
            ("CVV Mismatch Hold", "cvv_matched", "==", "No", "HOLD & VERIFY"),
            ("High Velocity Alert", "daily_transaction_count", ">=", "10", "MANUAL REVIEW")
        ]
        cursor.executemany("""
            INSERT INTO rules(rule_name, condition_field, condition_operator, condition_value, action)
            VALUES(?,?,?,?,?)
        """, default_rules)

    conn.commit()
    conn.close()


# -----------------------------
# Rules Management Helpers
# -----------------------------
def get_all_rules():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rules ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def insert_rule(name, field, operator, value, action):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO rules(rule_name, condition_field, condition_operator, condition_value, action)
        VALUES(?,?,?,?,?)
    """, (name, field, operator, value, action))
    conn.commit()
    conn.close()


def delete_rule(rule_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM rules WHERE id = ?", (rule_id,))
    conn.commit()
    conn.close()


def toggle_rule(rule_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("UPDATE rules SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END WHERE id = ?", (rule_id,))
    conn.commit()
    conn.close()


# -----------------------------
# Insert Prediction
# -----------------------------
def insert_prediction(data):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO transactions(
            transaction_id, customer_id, card_number, customer_age, gender, amount,
            merchant_category, city, state, country, device_type, card_present,
            cvv_matched, international_transaction, daily_transaction_count,
            previous_fraud_count, prediction, probability, risk_score,
            risk_level, recommendation, status, fraud_reason, created_at
        )
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        data.get("transaction_id"),
        data.get("customer_id"),
        data.get("card_number"),
        data.get("customer_age"),
        data.get("gender"),
        data.get("amount"),
        data.get("merchant_category"),
        data.get("city"),
        data.get("state"),
        data.get("country"),
        data.get("device_type"),
        data.get("card_present"),
        data.get("cvv_matched"),
        data.get("international_transaction"),
        data.get("daily_transaction_count"),
        data.get("previous_fraud_count"),
        data.get("Prediction", data.get("prediction")),
        data.get("Probability", data.get("probability")),
        data.get("Risk Score", data.get("risk_score")),
        data.get("Risk Level", data.get("risk_level")),
        data.get("Recommendation", data.get("recommendation")),
        data.get("Status", data.get("status")),
        data.get("Fraud Reason", data.get("fraud_reason")),
        data.get("created_at")
    ))

    conn.commit()
    conn.close()


# -----------------------------
# Get Paginated and Filtered Transactions
# -----------------------------
def get_paginated_transactions(limit, offset, search_query=None, filters=None, fraud_only=False):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = "SELECT * FROM transactions WHERE 1=1"
    count_query = "SELECT COUNT(*) FROM transactions WHERE 1=1"
    params = []

    if fraud_only:
        query += " AND prediction = 'Fraud'"
        count_query += " AND prediction = 'Fraud'"

    if search_query:
        search_query = search_query.strip()
        query += """ AND (
            transaction_id LIKE ? OR 
            customer_id LIKE ? OR 
            card_number LIKE ? OR 
            merchant_category LIKE ? OR 
            city LIKE ? OR 
            state LIKE ? OR 
            country LIKE ?
        )"""
        count_query += """ AND (
            transaction_id LIKE ? OR 
            customer_id LIKE ? OR 
            card_number LIKE ? OR 
            merchant_category LIKE ? OR 
            city LIKE ? OR 
            state LIKE ? OR 
            country LIKE ?
        )"""
        like_param = f"%{search_query}%"
        params.extend([like_param] * 7)

    if filters:
        if filters.get("risk_level"):
            query += " AND UPPER(risk_level) = ?"
            count_query += " AND UPPER(risk_level) = ?"
            params.append(filters["risk_level"].strip().upper())
        if filters.get("status"):
            query += " AND status = ?"
            count_query += " AND status = ?"
            params.append(filters["status"].strip())
        if filters.get("device_type"):
            query += " AND device_type = ?"
            count_query += " AND device_type = ?"
            params.append(filters["device_type"].strip())
        if filters.get("min_amount"):
            try:
                query += " AND amount >= ?"
                count_query += " AND amount >= ?"
                params.append(float(filters["min_amount"]))
            except ValueError:
                pass
        if filters.get("max_amount"):
            try:
                query += " AND amount <= ?"
                count_query += " AND amount <= ?"
                params.append(float(filters["max_amount"]))
            except ValueError:
                pass

    query += " ORDER BY id DESC LIMIT ? OFFSET ?"

    cursor.execute(count_query, params)
    total_count = cursor.fetchone()[0]

    query_params = params + [limit, offset]
    cursor.execute(query, query_params)
    rows = cursor.fetchall()

    conn.close()
    return [dict(row) for row in rows], total_count


# -----------------------------
# Get Transaction By ID
# -----------------------------
def get_transaction_by_id(transaction_id):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transactions WHERE transaction_id = ?", (transaction_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# -----------------------------
# Get Customer History
# -----------------------------
def get_customer_history(customer_id, current_txn_id=None):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if current_txn_id:
        cursor.execute("""
            SELECT * FROM transactions 
            WHERE customer_id = ? AND transaction_id != ? 
            ORDER BY id DESC LIMIT 10
        """, (customer_id, current_txn_id))
    else:
        cursor.execute("""
            SELECT * FROM transactions 
            WHERE customer_id = ? 
            ORDER BY id DESC LIMIT 10
        """, (customer_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# -----------------------------
# Dashboard Counts
# -----------------------------
def dashboard_counts():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM transactions")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM transactions WHERE prediction='Fraud'")
    fraud = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM transactions WHERE prediction='Genuine'")
    genuine = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM transactions WHERE status='Blocked'")
    blocked = cursor.fetchone()[0]

    cursor.execute("""
        SELECT SUM(amount), AVG(amount), MAX(amount) 
        FROM transactions WHERE prediction='Fraud'
    """)
    amt_row = cursor.fetchone()
    total_fraud_amount = amt_row[0] or 0.0
    avg_fraud_amount = amt_row[1] or 0.0
    highest_fraud_amount = amt_row[2] or 0.0

    cursor.execute("""
        SELECT COUNT(*) FROM transactions 
        WHERE prediction='Fraud' AND DATE(created_at) = DATE('now')
    """)
    today_fraud = cursor.fetchone()[0]

    conn.close()

    return {
        "total": total,
        "fraud": fraud,
        "genuine": genuine,
        "fraud_percentage": round((fraud / total * 100), 2) if total > 0 else 0.0,
        "total_fraud_amount": round(total_fraud_amount, 2),
        "avg_fraud_amount": round(avg_fraud_amount, 2),
        "highest_fraud_amount": round(highest_fraud_amount, 2),
        "today_fraud_count": today_fraud,
        "blocked_cards": blocked
    }


# -----------------------------
# Recent Transactions
# -----------------------------
def get_recent_transactions(limit=10):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            transaction_id, customer_id, card_number, amount,
            prediction, risk_score, risk_level, status, created_at
        FROM transactions
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# -----------------------------
# Geo Fraud Points for Map
# -----------------------------
def get_geo_fraud_points():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT city, country, COUNT(*) as fraud_count, SUM(amount) as total_amount
        FROM transactions
        WHERE prediction='Fraud'
        GROUP BY city
        ORDER BY fraud_count DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    points = []
    for r in rows:
        city = r["city"]
        coords = CITY_COORDINATES.get(city, [19.0760, 72.8777])
        points.append({
            "city": city,
            "country": r["country"],
            "count": r["fraud_count"],
            "amount": round(r["total_amount"], 2),
            "lat": coords[0],
            "lng": coords[1]
        })
    return points


# -----------------------------
# Analytics Data
# -----------------------------
def get_analytics_data():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT risk_level, COUNT(*) as count 
        FROM transactions WHERE prediction='Fraud' 
        GROUP BY risk_level
    """)
    risk_level_dist = {row['risk_level']: row['count'] for row in cursor.fetchall()}

    cursor.execute("""
        SELECT transaction_id, risk_score, amount 
        FROM transactions WHERE prediction='Fraud' 
        ORDER BY risk_score DESC LIMIT 15
    """)
    top_score_cases = [dict(row) for row in cursor.fetchall()]

    cursor.execute("""
        SELECT 
            SUM(CASE WHEN amount < 500 THEN 1 ELSE 0 END) as tier1,
            SUM(CASE WHEN amount >= 500 AND amount < 2000 THEN 1 ELSE 0 END) as tier2,
            SUM(CASE WHEN amount >= 2000 AND amount < 5000 THEN 1 ELSE 0 END) as tier3,
            SUM(CASE WHEN amount >= 5000 AND amount < 10000 THEN 1 ELSE 0 END) as tier4,
            SUM(CASE WHEN amount >= 10000 THEN 1 ELSE 0 END) as tier5
        FROM transactions WHERE prediction='Fraud'
    """)
    amount_dist_row = cursor.fetchone()
    amount_dist = {
        "Under ₹500": amount_dist_row['tier1'] or 0,
        "₹500 - ₹2,000": amount_dist_row['tier2'] or 0,
        "₹2,000 - ₹5,000": amount_dist_row['tier3'] or 0,
        "₹5,000 - ₹10,000": amount_dist_row['tier4'] or 0,
        "Over ₹10,000": amount_dist_row['tier5'] or 0
    }

    cursor.execute("""
        SELECT transaction_id, customer_id, amount, risk_score, risk_level, status, created_at 
        FROM transactions ORDER BY risk_score DESC LIMIT 10
    """)
    top_10_high_risk = [dict(row) for row in cursor.fetchall()]

    cursor.execute("""
        SELECT DATE(created_at) as date, COUNT(*) as count, SUM(amount) as amount
        FROM transactions WHERE prediction='Fraud' 
        GROUP BY DATE(created_at) ORDER BY date DESC LIMIT 15
    """)
    daily_trends = [dict(row) for row in cursor.fetchall()]
    daily_trends.reverse()

    cursor.execute("""
        SELECT merchant_category, COUNT(*) as count, SUM(amount) as total_amount
        FROM transactions WHERE prediction='Fraud' 
        GROUP BY merchant_category ORDER BY count DESC LIMIT 10
    """)
    merchant_fraud = [dict(row) for row in cursor.fetchall()]

    cursor.execute("""
        SELECT city, COUNT(*) as count, SUM(amount) as total_amount
        FROM transactions WHERE prediction='Fraud' 
        GROUP BY city ORDER BY count DESC LIMIT 10
    """)
    city_fraud = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return {
        "risk_level_distribution": risk_level_dist,
        "top_score_cases": top_score_cases,
        "amount_distribution": amount_dist,
        "top_10_high_risk": top_10_high_risk,
        "daily_trends": daily_trends,
        "merchant_fraud": merchant_fraud,
        "city_fraud": city_fraud
    }