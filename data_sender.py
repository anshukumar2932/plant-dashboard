import sqlite3
import random
import time
from datetime import datetime

def create_db():
    try:
        conn = sqlite3.connect('data.db')
        cursor = conn.cursor()
        
        # First check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cement_data'")
        if not cursor.fetchone():
            # Create table if it doesn't exist
            cursor.execute('''
                CREATE TABLE cement_data (
                    timestamp TEXT,
                    total_cement_produced REAL,
                    production_target REAL,
                    oee REAL,
                    energy_consumption REAL,
                    clinker_production_rate REAL,
                    kiln_running_hours REAL,
                    kiln_temperature REAL,
                    mill_throughput REAL,
                    bagging_output REAL,
                    downtime_kiln REAL,
                    downtime_crusher REAL,
                    downtime_mill REAL,
                    scheduled_maintenance REAL,
                    unscheduled_maintenance REAL,
                    mttr REAL,
                    mtbf REAL,
                    blaine_fineness REAL,
                    lime_saturation_factor REAL,
                    free_lime_content REAL,
                    compressive_strength_2d REAL,
                    compressive_strength_7d REAL,
                    compressive_strength_28d REAL,
                    dust_emissions REAL,
                    co2_emissions REAL,
                    water_usage REAL,
                    noise_levels REAL,
                    limestone_stock REAL,
                    clinker_stock REAL,
                    cement_stock REAL,
                    hourly_production REAL
                )
            ''')
            print("✅ Table 'cement_data' created successfully")
        
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")

def rand_val(mean, std_dev, min_val=None, max_val=None, round_to=2):
    val = random.gauss(mean, std_dev)
    if min_val is not None:
        val = max(min_val, val)
    if max_val is not None:
        val = min(max_val, val)
    return round(val, round_to)

def get_last_production():
    try:
        conn = sqlite3.connect('data.db')
        cursor = conn.cursor()
        cursor.execute('SELECT total_cement_produced FROM cement_data ORDER BY timestamp DESC LIMIT 1')
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0
    except sqlite3.Error as e:
        print(f"❌ Error getting last production: {e}")
        return 0
def get_last_bag():
    try:
        conn = sqlite3.connect('data.db')
        cursor = conn.cursor()
        cursor.execute('SELECT bagging_output FROM cement_data ORDER BY timestamp DESC LIMIT 1')
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0
    except sqlite3.Error as e:
        print(f"❌ Error getting last production: {e}")
        return 0

def generate_sample_data():
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    last_production = get_last_production()
    last_bag=get_last_bag()
    hourly_production = random.randint(1,3)
    total_cement_produced = last_production + hourly_production*0.035
    bag_output=int(total_cement_produced*1000/50)
    return (
        timestamp,
        total_cement_produced,
        120,                              # production_target
        rand_val(90, 5, 70, 100),        # oee
        rand_val(105, 10, 80, 140),      # energy_consumption
        284,      # clinker_production_rate
        rand_val(5.5, 2.5, 1, 12),       # kiln_running_hours
        rand_val(1200, 50, 1000, 1600),  # kiln_temperature
        rand_val(60, 15, 45, 80),        # mill_throughput
        bag_output,      # bagging_output
        rand_val(0.5, 0.4, 0.05, 2),     # downtime_kiln
        rand_val(0.4, 0.3, 0.05, 2),     # downtime_crusher
        rand_val(0.4, 0.3, 0.05, 2),     # downtime_mill
        rand_val(0.25, 0.2, 0.05, 1),    # scheduled_maintenance
        rand_val(0.3, 0.25, 0.05, 1),    # unscheduled_maintenance
        rand_val(2, 1.2, 0.5, 5),        # mttr
        rand_val(75, 25, 30, 150),       # mtbf
        rand_val(3350, 100, 3100, 3600), # blaine_fineness
        rand_val(1.0, 0.08, 0.85, 1.15), # lime_saturation_factor
        rand_val(2, 0.6, 0.5, 3.5),      # free_lime_content
        rand_val(40, 3, 30, 50),         # compressive_strength_2d
        rand_val(43, 3, 35, 55),         # compressive_strength_7d
        rand_val(45, 3, 38, 60),         # compressive_strength_28d
        rand_val(45, 5, 30, 70),         # dust_emissions
        rand_val(750, 30, 680, 820),     # co2_emissions
        rand_val(200, 15, 150, 250),     # water_usage
        rand_val(88, 2, 80, 95),         # noise_levels
        rand_val(1000, 100, 800, 1300),  # limestone_stock
        rand_val(825, 75, 650, 1000),    # clinker_stock
        rand_val(1150, 100, 900, 1400),  # cement_stock
        hourly_production                # hourly_production
    )

def insert_data(data):
    try:
        conn = sqlite3.connect('data.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO cement_data VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?
            )
        ''', data)
        conn.commit()
        conn.close()
        print(f"✅ Data inserted at {data[0]}")
    except sqlite3.Error as e:
        print(f"❌ Error inserting data: {e}")

def main_data():
    # First ensure database and table exist
    create_db()
    
    # Insert initial data point
    initial_data = generate_sample_data()
    insert_data(initial_data)
    
    # Start periodic data generation
    while True:
        data = generate_sample_data()
        insert_data(data)
        time.sleep(5)  # 5-second intervals for demo (use 60 for production)

