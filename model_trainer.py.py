import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline

# Sample training data for Civic Problems
data = [
    ("There is a massive water leak near main street road", "Water/Drainage", "High"),
    ("Garbage bin is overflowing and smelling bad", "Waste Management", "Medium"),
    ("Streetlight is broken and road is completely dark at night", "Electricity/Lighting", "Medium"),
    ("Big pothole on the road caused an accident", "Road Repair", "High"),
    ("Drainage water is coming out on the street", "Water/Drainage", "Critical"),
    ("Trash hasn't been collected for 3 days", "Waste Management", "Low"),
    ("Sparking in electric transformer on main pole", "Electricity/Lighting", "Critical"),
    ("Damaged road needs urgent fixing", "Road Repair", "High")
]

texts, categories, priorities = zip(*[(d[0], d[1], d[2]) for d in data])

# Pipeline for Category Prediction
cat_model = Pipeline([
    ('tfidf', TfidfVectorizer()),
    ('clf', RandomForestClassifier(n_estimators=10, random_state=42))
])
cat_model.fit(texts, categories)

# Pipeline for Priority Prediction
prio_model = Pipeline([
    ('tfidf', TfidfVectorizer()),
    ('clf', RandomForestClassifier(n_estimators=10, random_state=42))
])
prio_model.fit(texts, priorities)

# Save Models
joblib.dump(cat_model, 'category_model.pkl')
joblib.dump(prio_model, 'priority_model.pkl')
print("AI Models Trained and Saved Successfully!")