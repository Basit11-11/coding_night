from flask import Flask, request, jsonify, render_template
import sqlite3
import re
from stats_engine import CivicStatsEngine

app = Flask(__name__)

# ---------------------------------------------------------
# DATABASE INITIALIZATION
# ---------------------------------------------------------
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
    
    cursor.execute("SELECT COUNT(*) FROM complaints")
    if cursor.fetchone()[0] == 0:
        sample_records = [
            ("Water main line burst on street", "Water/Drainage", "High", "Sector 1", 14.5),
            ("Gutter blockage overflowing", "Water/Drainage", "Critical", "Block C", 36.0),
            ("Garbage pile near market", "Waste Management", "Medium", "Main Bazaar", 8.2),
            ("Trash collector missed street", "Waste Management", "Low", "Zone 4", 5.0),
            ("Street light pole dark", "Electricity/Lighting", "Medium", "Street 9", 22.4),
            ("Sparks from electric transformer", "Electricity/Lighting", "Critical", "Sector 2", 3.5),
            ("Deep road crater pothole", "Road Repair", "High", "Highway North", 48.0),
            ("Cracked road sidewalk", "Road Repair", "Low", "Block A", 18.0),
            ("Dark unlit road", "Public Safety", "High", "Sector 3", 12.0),
            ("Severe water pipeline leak", "Water/Drainage", "Critical", "Sector 1", 96.0)
        ]
        cursor.executemany('''
            INSERT INTO complaints (description, category, priority, location, resolution_time_hrs)
            VALUES (?, ?, ?, ?, ?)
        ''', sample_records)
        
    conn.commit()
    conn.close()

init_db()


# ---------------------------------------------------------
# MULTILINGUAL AI & RULE CLASSIFIER (English, Roman Urdu, Urdu)
# ---------------------------------------------------------
def smart_ai_classifier(text):
    clean_text = text.lower().strip()
    
    # 1. Check text length
    if len(clean_text) < 4:
        return "General / Unclassified", "Low"

    # Multilingual Dictionary (English, Roman Urdu, Urdu script)
    categories_map = {
        "Water/Drainage": [
            "water", "drain", "drainage", "pipe", "leak", "sewage", "gutter", "flood", "overflow",
            "paani", "pani", "nal", "gali", "nalee", "guttar", "pipleline", "seewage",
            "پانی", "گٹر", "سیوریج", "پائپ"
        ],
        "Waste Management": [
            "garbage", "trash", "waste", "dump", "bin", "smell", "dirt", "rubbish", "clean", "sweeper",
            "kachra", "kachray", "kchra", "gandagi", "badboo", "safai", "jhroo",
            "کچرا", "گندگی", "بدبو", "صفائی"
        ],
        "Electricity/Lighting": [
            "light", "electricity", "electric", "power", "wire", "spark", "transformer", "pole", "dark", "current",
            "bijli", "taar", "tarein", "dhamaka", "andhera", "andhera", "bulb",
            "بجلی", "تار", "ٹرانسفارمر", "اندھیرا"
        ],
        "Road Repair": [
            "road", "pothole", "street", "asphalt", "crater", "footpath", "sidewalk", "crack", "pavement", "highway",
            "sarak", "sadak", "gadda", "gadde", "khadday", "khadda", "rasta", "raasta",
            "سڑک", "گڑھا", "راستہ"
        ]
    }

    # Match category
    matched_cat = None
    for category, words in categories_map.items():
        for word in words:
            if word in clean_text:
                matched_cat = category
                break
        if matched_cat:
            break

    # STRICT FALLBACK: If NO match is found -> ALWAYS General / Unclassified
    if not matched_cat:
        return "General / Unclassified", "Low"

    # Priority determination
    critical_words = ["fire", "spark", "explosion", "emergency", "danger", "burst", "aag", "dhamaka", "khatra", "آگ", "خطرہ"]
    high_words = ["heavy", "severe", "blocked", "overflowing", "deep", "main", "zyada", "ziyada", "بڑا", "زیادہ"]

    if any(cw in clean_text for cw in critical_words):
        priority = "Critical"
    elif any(hw in clean_text for hw in high_words):
        priority = "High"
    else:
        priority = "Medium"

    return matched_cat, priority


# ---------------------------------------------------------
# ROUTES
# ---------------------------------------------------------
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

    # Classify input
    pred_category, pred_priority = smart_ai_classifier(text)

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

    cursor.execute("SELECT category FROM complaints")
    categories = [row[0] for row in cursor.fetchall() if row[0]]

    cursor.execute("SELECT resolution_time_hrs FROM complaints WHERE resolution_time_hrs IS NOT NULL")
    res_times = [row[0] for row in cursor.fetchall()]

    if not res_times:
        res_times = [12.5, 24.0, 18.2, 48.0, 15.0, 6.5, 72.0, 22.1, 19.5, 14.0]

    conn.close()

    cat_dist = CivicStatsEngine.category_frequency_distribution(categories) if categories else {}

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