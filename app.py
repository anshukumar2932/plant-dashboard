from flask import Flask, render_template, request, jsonify, session, Response
from datetime import timedelta
import time
import json
import sqlite3
import threading
import pickle
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest
from data_sender import * 
import numpy as np

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'Supper'
app.permanent_session_lifetime = timedelta(seconds=300)

# ========== Load Pre-trained Models ==========
# Load the pre-trained Isolation Forest model
with open('isolation_forest_model.pkl', 'rb') as model_file:
    isolation_forest_model = pickle.load(model_file)

# Load the pre-trained scaler
with open('scaler.pkl', 'rb') as scaler_file:
    scaler = pickle.load(scaler_file)

# ========== DB Fetch ==========
def query_db():
    conn = sqlite3.connect("data.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM cement_data ORDER BY timestamp DESC LIMIT 10;")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"DB Error: {e}")
        return []
    finally:
        conn.close()

# ========== Anomaly Detection ==========
def detect_anomalies(data):
    # Define the features
    features = ['total_cement_produced', 'production_target', 'oee', 'energy_consumption',
                'clinker_production_rate', 'kiln_running_hours', 'kiln_temperature',
                'mill_throughput', 'bagging_output', 'downtime_kiln', 'downtime_crusher',
                'downtime_mill', 'scheduled_maintenance', 'unscheduled_maintenance', 'mttr',
                'mtbf', 'blaine_fineness', 'lime_saturation_factor', 'free_lime_content',
                'compressive_strength_2d', 'compressive_strength_7d', 'compressive_strength_28d',
                'dust_emissions', 'co2_emissions', 'water_usage', 'noise_levels', 'limestone_stock',
                'clinker_stock', 'cement_stock', 'hourly_production']

    # Convert the incoming data to DataFrame
    df = pd.DataFrame([data], columns=features)

    # Preprocess and scale the data
    X_scaled = scaler.transform(df)

    # Predict anomalies
    predictions = isolation_forest_model.predict(X_scaled)

    # Convert predictions from [-1, 1] to [0, 1] (0 = normal, 1 = anomaly)
    anomalies = (predictions == -1).astype(int)

    # Add anomaly predictions to the data
    data['anomaly'] = anomalies[0]

    return data

# ========== Threshold Logic ==========
def check_thresholds(data):
    thresholds = {
        "kiln_temperature": (1100, 1350),
        "dust_emissions": (0, 30),
        "co2_emissions": (0, 800),
        "energy_consumption": (0, 130),
        "oee": (65, 100),
        "total_cement_produced": (0, 10000),
        "bagging_output": (0, 500),
        "clinker_production_rate": (0,1000)
    }

    alerts = {}
    for key, (low, high) in thresholds.items():
        val = data.get(key)
        if key!="bagging_output":
            if val is None:
                alerts[key] = "unknown"
            elif val < low:
                alerts[key] = "warning"
            elif val > high:
                alerts[key] = "danger"
            else:
                alerts[key] = "safe"
        else:
            if val < low:
                alerts[key] = "low"
            elif val > high:
                alerts[key] = "ok"
            else:
                alerts[key] = "excellent"
    return alerts

# Convert numpy.int64 to int
def convert_int64(obj):
    """Recursively convert numpy int64 to Python int."""
    if isinstance(obj, np.int64):
        return int(obj)
    elif isinstance(obj, dict):
        return {key: convert_int64(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_int64(item) for item in obj]
    return obj

@app.route('/')
def entry_page():
    return render_template('dashboard.html')

@app.route('/ws/data')
def get_data():
    def generate():
        while True:
            data = query_db()
            latest = data[0] if data else {}
            if latest:
                # Perform anomaly detection
                latest = detect_anomalies(latest)

                # Check thresholds and generate alerts
                alerts = check_thresholds(latest)
            else:
                alerts = {}

            # Convert data before sending
            latest = convert_int64(latest)
            alerts = convert_int64(alerts)

            # Send data to client as JSON
            json_data = json.dumps({"latest": latest, "alerts": alerts})
            print(json_data)
            yield f"data: {json_data}\n\n"
            time.sleep(5)  # Data update frequency
    return Response(generate(), content_type='text/event-stream')

if __name__ == '__main__':
    # Start main_data in a separate thread (if necessary)
    data_thread = threading.Thread(target=main_data, daemon=True)
    data_thread.start()

    # Start Flask app
    app.run(debug=True, threaded=True)
