from flask import Flask, request, jsonify, render_template
import sqlite3
import os
import json
from openai import OpenAI
from stats_engine import CivicStatsEngine

app = Flask(__name__)

# Initialize OpenAI Client
# Apni actual API Key yahan paste karein (e.g., 'sk-proj-xxxx...')
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY"))

# ---------------------------------------------------------
# 1. Database Setup
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
    
    # Initial sample benchmark data
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
# 2. OpenAI AI Processing Function
# ---------------------------------------------------------
def analyze_complaint_with_openai(user_description):
    """
    Sends description to OpenAI API to get JSON classification:
    - category
    - priority
    """
    prompt = f"""
    You are an AI Civic Assistant. Analyze the following civic complaint description and categorize it.
    
    Complaint Description: "{user_description}"
    
    Available Categories:
    - Water/Drainage
    - Waste Management
    - Electricity/Lighting
    - Road Repair
    - Public Safety
    - General / Unclassified (Use this for random, greeting, nonsense, or non-civic text)

    Available Priorities:
    - Critical (Immediate danger, fire, severe flood, spark)
    - High (Major roads, heavy leakage, major issue)
    - Medium (Moderate inconvenience)
    - Low (Minor maintenance, trash collection)

    Return ONLY a valid JSON object in this exact format:
    {{"category": "<Category Name>", "priority": "<Priority Level>"}}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Fast and cost-effective model
            messages=[
                {"role": "system", "content": "You are a precise JSON-only classifier for civic issues."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        
        result_json = json.loads(response.choices[0].message.content)
        category = result_json.get("category", "General / Unclassified")
        priority = result_json.get("priority", "Low")
        return category, priority

    except Exception as e:
        print("OpenAI API Error:", e)
        # Fallback if API fails or key is missing
        return "General / Unclassified", "Low"


# ---------------------------------------------------------
# 3. API Endpoints
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

    # Call OpenAI to process description dynamically
    pred_category, pred_priority = analyze_complaint_with_openai(text)

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