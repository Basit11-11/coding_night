from flask import Flask, request, jsonify, render_template
import sqlite3
import joblib
import os
import numpy as np
from datetime import datetime
from stats_engine import CivicStatsEngine

app = Flask(__name__)

# Load AI Models
if not (os.path.exists('category_model.pkl') and os.path.exists('priority_model.pkl')):
    import model_trainer

cat_model = joblib.load('category_model.pkl')
prio_model = joblib.load('priority_model.pkl')

# Database Initialization
def init_db():
    conn = sqlite3.connect('civic_service.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            category TEXT,
            priority TEXT,
            location TEXT,
            status TEXT DEFAULT 'Open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolution_time_hrs REAL DEFAULT NULL
        )
    ''')
    
    # Insert initial benchmark resolution times if database is empty
    cursor.execute("SELECT COUNT(*) FROM complaints")
    if cursor.fetchone()[0] == 0:
        sample_records = [
            ("Water leak on main road", "Water/Drainage", "High", "Sector 1", 14.5),
            ("Drainage blockage", "Water/Drainage", "Critical", "Block C", 36.0),
            ("Overflowing garbage bin", "Waste Management", "Medium", "Main Bazaar", 8.2),
            ("Trash truck issue", "Waste Management", "Low", "Zone 4", 5.0),
            ("Broken street light", "Electricity/Lighting", "Medium", "Street 9", 22.4),
            ("Sparking wire pole", "Electricity/Lighting", "Critical", "Sector 2", 3.5),
            ("Deep road pothole", "Road Repair", "High", "Highway North", 48.0),
            ("Cracked sidewalk", "Road Repair", "Low", "Block A", 18.0),
            ("Dark unlit road", "Public Safety", "High", "Sector 3", 12.0),
            ("Severe water issue", "Water/Drainage", "Critical", "Sector 1", 96.0)
        ]
        cursor.executemany('''
            INSERT INTO complaints (description, category, priority, location, resolution_time_hrs)
            VALUES (?, ?, ?, ?, ?)
        ''', sample_records)
        
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/submit', methods=['POST'])
def submit_complaint():
    data = request.json or {}
    text = data.get('description', '').strip()
    location = data.get('location', 'General').strip()

    if not text:
        return jsonify({"error": "Description is required"}), 400

    cleaned_text = text.lower()

    # -------------------------------------------------------------
    # STRICT HYBRID FILTER: Detect Random Prompts vs Civic Issues
    # -------------------------------------------------------------
    civic_dictionary = {
        "Water/Drainage": ["water", "drain", "drainage", "pipe", "leak", "sewage", "gutter", "flood", "overflow"],
        "Waste Management": ["garbage", "trash", "waste", "dump", "bin", "smell", "dirt", "rubbish", "cleanliness"],
        "Electricity/Lighting": ["light", "electricity", "electric", "power", "wire", "spark", "transformer", "pole", "dark", "current"],
        "Road Repair": ["road", "pothole", "street", "asphalt", "crater", "footpath", "sidewalk", "crack", "pavement", "highway"]
    }

    # Check if text matches any valid civic keyword
    matched_category = None
    for category, keywords in civic_dictionary.items():
        if any(kw in cleaned_text for kw in keywords):
            matched_category = category
            break

    # If NO civic words found or input is too short -> Mark as General / Unclassified
    if matched_category is None:
        pred_category = "General / Unclassified"
        pred_priority = "Low"
    else:
        try:
            # High Confidence ML prediction if keywords exist
            cat_probs = cat_model.predict_proba([text])[0]
            max_cat_prob = float(np.max(cat_probs))

            if max_cat_prob > 0.25:
                pred_category = cat_model.predict([text])[0]
                pred_priority = prio_model.predict([text])[0]
            else:
                pred_category = matched_category
                pred_priority = "Medium"
        except Exception:
            pred_category = matched_category
            pred_priority = "Medium"

    # Save to Database
    conn = sqlite3.connect('civic_service.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO complaints (description, category, priority, location)
        VALUES (?, ?, ?, ?)
    ''', (text, pred_category, pred_priority, location))
    conn.commit()
    complaint_id = cursor.lastrowid
    conn.close()

    return jsonify({
        "status": "success",
        "complaint_id": complaint_id,
        "ai_output": {
            "category": pred_category,
            "priority": pred_priority
        }
    })

@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    conn = sqlite3.connect('civic_service.db')
    cursor = conn.cursor()

    # Fetch Categories
    cursor.execute("SELECT category FROM complaints")
    categories = [row[0] for row in cursor.fetchall() if row[0]]

    # Fetch Resolution Times
    cursor.execute("SELECT resolution_time_hrs FROM complaints WHERE resolution_time_hrs IS NOT NULL")
    res_times = [row[0] for row in cursor.fetchall()]

    # Default fallback data if resolution_time_hrs column is empty
    if not res_times:
        res_times = [12.5, 24.0, 18.2, 48.0, 15.0, 6.5, 72.0, 22.1, 19.5, 14.0]

    conn.close()

    # Calculate Frequency Distribution
    cat_dist = CivicStatsEngine.category_frequency_distribution(categories) if categories else {}

    # Calculate Descriptive Statistics
    if hasattr(CivicStatsEngine, 'calculate_resolution_time_stats'):
        res_stats = CivicStatsEngine.calculate_resolution_time_stats(res_times)
    elif hasattr(CivicStatsEngine, 'calculate_resolution_stats'):
        res_stats = CivicStatsEngine.calculate_resolution_stats(res_times)
    else:
        res_stats = {}

    return jsonify({
        "total_complaints": len(categories),
        "category_distribution": cat_dist,
        "resolution_time_statistics": res_stats
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)