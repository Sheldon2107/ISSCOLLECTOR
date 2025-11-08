import requests
import sqlite3
import time
from datetime import datetime

# --- Configuration ---
API_URL = "https://api.wheretheiss.at/v1/satellites/25544"
DATABASE_FILE = "iss_telemetry.db"
COLLECTION_INTERVAL_SEC = 1.1 # Respecting the ~1 req/sec rate limit
DAYS_OF_COLLECTION = 3
TOTAL_COLLECTIONS = int(DAYS_OF_COLLECTION * 24 * 60 * 60 / COLLECTION_INTERVAL_SEC)
# Expected data points for 3 days: 3 * 24 * 3600 / 1.1 ≈ 235,000 records

# --- 1. Database Initialization ---
def setup_database():
    """Initializes the SQLite database and creates the telemetry table."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    # INTEGER PRIMARY KEY is auto-incrementing in SQLite
    # Storing timestamp as a Unix INTEGER is efficient for querying
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS telemetry (
            id INTEGER PRIMARY KEY,
            timestamp_utc INTEGER NOT NULL,
            latitude REAL,
            longitude REAL,
            altitude REAL,
            velocity REAL
        )
    """)
    conn.commit()
    conn.close()
    print(f"Database {DATABASE_FILE} setup complete.")
    

# --- 2. Data Fetcher and Inserter ---
def fetch_and_store_data():
    """Fetches ISS data and inserts it into the database."""
    try:
        response = requests.get(API_URL, timeout=5)
        response.raise_for_status() # Raises an exception for HTTP errors (4xx or 5xx)
        data = response.json()
        
        # Ensure data is valid before insertion
        if 'latitude' in data and 'longitude' in data and 'timestamp' in data:
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            
            # Use the 'timestamp' directly from the API (Unix time)
            cursor.execute("""
                INSERT INTO telemetry (timestamp_utc, latitude, longitude, altitude, velocity)
                VALUES (?, ?, ?, ?, ?)
            """, (
                data['timestamp'],
                data['latitude'],
                data['longitude'],
                data['altitude'],
                data['velocity']
            ))
            conn.commit()
            conn.close()
            
            current_time = datetime.fromtimestamp(data['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
            print(f"[{current_time} UTC] Logged: Lat={data['latitude']:.2f}, Lon={data['longitude']:.2f}, Alt={data['altitude']:.2f}km")
        else:
            print(f"Error: Incomplete data received: {data}")
            
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from API: {e}")
    except sqlite3.Error as e:
        print(f"Database error: {e}")

# --- 3. Main Loop ---
def run_collector():
    setup_database()
    count = 0
    print(f"\n--- Starting continuous collection for {DAYS_OF_COLLECTION} days ({TOTAL_COLLECTIONS} records) ---")
    
    while count < TOTAL_COLLECTIONS:
        fetch_and_store_data()
        count += 1
        time.sleep(COLLECTION_INTERVAL_SEC) # Throttle to respect API limit
        
    print("\n--- 3-day collection target reached. Collector shutting down. ---")

if __name__ == '__main__':
    run_collector()

# To run this script: python iss_collector.py
