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
import numpy as np
import os

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'Supper')
app.permanent_session_lifetime = timedelta(seconds=300)

# ========== Load Pre-trained Models ==========
def load_model_assets():
    try:
        # Load the pre-trained Isolation Forest model
        with open('isolation_forest_model.pkl', 'rb') as model_file:
            isolation_forest_model = pickle.load(model_file)

        # Load the pre-trained scaler
        with open('scaler.pkl', 'rb') as scaler_file:
            scaler = pickle.load(scaler_file)
            
        return isolation_forest_model, scaler
    except Exception as e:
        print(f"Error loading model assets: {e}")
        return None, None

isolation_forest_model, scaler = load_model_assets()

# ========== DB Fetch ==========
def query_db():
    # Use Render's PostgreSQL if available, otherwise fall back to SQLite
    db_url = os.environ.get('DATABASE_URL', 'sqlite:///data.db')
    
    if db_url.startswith('postgres://'):
        import psycopg2
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
        try:
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM cement_data ORDER BY timestamp DESC LIMIT 10;")
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            print(f"PostgreSQL Error: {e}")
            return []
        finally:
            if conn:
                conn.close()
    else:
        # SQLite fallback
        try:
            conn = sqlite3.connect("data.db")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM cement_data ORDER BY timestamp DESC LIMIT 10;")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"SQLite Error: {e}")
            return []
        finally:
            if conn:
                conn.close()

# ========== Anomaly Detection ==========
def detect_anomalies(data):
    if isolation_forest_model is None or scaler is None:
        data['anomaly'] = 0  # Default to no anomaly if models aren't loaded
        return data

    # Define the features
    features = ['total_cement_produced', 'production_target', 'oee', 'energy_consumption',
                'clinker_production_rate', 'kiln_running_hours', 'kiln_temperature',
                'mill_throughput', 'bagging_output', 'downtime_kiln', 'downtime_crusher',
                'downtime_mill', 'scheduled_maintenance', 'unscheduled_maintenance', 'mttr',
                'mtbf', 'blaine_fineness', 'lime_saturation_factor', 'free_lime_content',
                'compressive_strength_2d', 'compressive_strength_7d', 'compressive_strength_28d',
                'dust_emissions', 'co2_emissions', 'water_usage', 'noise_levels', 'limestone_stock',
                'clinker_stock', 'cement_stock', 'hourly_production']

    try:
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
    except Exception as e:
        print(f"Anomaly detection error: {e}")
        data['anomaly'] = 0  # Default to no anomaly on error

    return data

# ========== Threshold Logic ==========
def check_thresholds(data):
    thresholds = {
        "kiln_temperature": (1100, 1350),
        "dust_emissions": (0, 50),
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
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
