import random
import time
import sqlite3
from datetime import datetime

# Function to simulate new data (temperature, pressure, etc.)
def generate_data():
    temperature = random.uniform(20.0, 100.0)  # Random temperature between 20-100°C
    pressure = random.uniform(80.0, 200.0)  # Random pressure between 80-200 psi
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {
        "timestamp": timestamp,
        "temperature": temperature,
        "pressure": pressure
    }

# Function to insert the generated data into the database
def insert_data_into_db(data):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS cement_data (
                        timestamp TEXT,
                        temperature REAL,
                        pressure REAL)''')
    
    cursor.execute('''INSERT INTO cement_data (timestamp, kiln_temperature,
                      VALUES (?, ?, ?)''', (data['timestamp'], data['temperature'], data['pressure']))
    
    conn.commit()
    conn.close()

# Continuously generate and insert data every 5 seconds (simulating real-time)
while True:
    data = generate_data()
    insert_data_into_db(data)
    print(f"Inserted data: {data}")
    time.sleep(5)  # Wait for 5 seconds before generating new data
