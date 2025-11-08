import requests
import sqlite3
import time
from datetime import datetime, timezone

# --- Configuration ---
API_URL = "https://api.wheretheiss.at/v1/satellites/25544"
DATABASE_FILE = "iss_telemetry.db"
# Set interval slightly above 1 second to respect the rate limit
COLLECTION_INTERVAL_SEC = 1.1 
DAYS_OF_COLLECTION = 3
# Calculate total collections needed for the duration
TOTAL_COLLECTIONS = int(DAYS_OF_COLLECTION * 24 * 60 * 60 / COLLECTION_INTERVAL_SEC) 

# --- 1. Database Initialization ---
def setup_database():
    """Initializes the SQLite database and creates the telemetry table."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    # Using REAL for precision in coordinates/altitude
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
        # Fetch data with a timeout to prevent hanging
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status() 
        data = response.json()
        
        # Validate required fields
        if all(key in data for key in ['latitude', 'longitude', 'timestamp', 'altitude', 'velocity']):
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            
            # Insert the raw Unix timestamp and telemetry data
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
            
            current_time = datetime.fromtimestamp(data['timestamp'], tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            print(f"[{current_time} UTC] Logged: Lat={data['latitude']:.2f}, Alt={data['altitude']:.2f}km")
        else:
            print(f"Warning: Incomplete data received at {datetime.now(timezone.utc)}: {data}")
            
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from API: {e}")
    except sqlite3.Error as e:
        print(f"Database error: {e}")

# --- 3. Main Loop ---
def run_collector():
    setup_database()
    count = 0
    print(f"\n--- Starting continuous collection for {DAYS_OF_COLLECTION} days ({TOTAL_COLLECTIONS} max records) ---")
    
    # Use a high number for continuous running, or your pre-calculated limit
    while True: # Changed to 'True' for continuous operation until manually stopped
        fetch_and_store_data()
        count += 1
        time.sleep(COLLECTION_INTERVAL_SEC) 
        
        # Optional: uncomment this to enforce the maximum count
        # if count >= TOTAL_COLLECTIONS:
        #     print("\n--- 3-day collection target reached. Collector shutting down. ---")
        #     break

if __name__ == '__main__':
    run_collector()
