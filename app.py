from flask import Flask, render_template, jsonify
import sqlite3
import time

app = Flask(__name__)
DATABASE_FILE = "iss_telemetry.db"

def get_db_connection():
    """Utility function to create a database connection."""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row # Allows accessing columns by name
    return conn

def calculate_analytics(conn):
    """Calculates Max/Min values and Altitude change."""
    cursor = conn.cursor()
    
    # Query 1: Max/Min Longitude and Altitude over all time
    analytics = cursor.execute("""
        SELECT 
            MAX(longitude) AS max_lon, 
            MIN(longitude) AS min_lon,
            MAX(altitude) AS max_alt,
            MIN(altitude) AS min_alt
        FROM telemetry
    """).fetchone()

    # Query 2: Altitude Change (Current vs. 1 hour ago)
    # Find the latest altitude and the altitude from ~1 hour ago (3600 seconds)
    
    latest_record = cursor.execute("SELECT timestamp_utc, altitude FROM telemetry ORDER BY timestamp_utc DESC LIMIT 1").fetchone()
    
    altitude_change_km = "N/A"
    
    if latest_record:
        latest_timestamp = latest_record['timestamp_utc']
        latest_altitude = latest_record['altitude']
        
        # Look for a record closest to 3600 seconds ago
        target_time = latest_timestamp - 3600
        
        # Find the record closest in time to the target time (absolute difference)
        past_record = cursor.execute("""
            SELECT altitude
            FROM telemetry
            ORDER BY ABS(timestamp_utc - ?)
            LIMIT 1
        """, (target_time,)).fetchone()
        
        if past_record:
            past_altitude = past_record['altitude']
            altitude_change_km = latest_altitude - past_altitude
    
    # Convert Row object to dict for easier jsonify
    result = dict(analytics) if analytics else {}
    result['altitude_change_km'] = f"{altitude_change_km:.3f}" if isinstance(altitude_change_km, float) else altitude_change_km
    
    return result

@app.route('/')
def index():
    """Serves the main dashboard page."""
    return render_template('dashboard.html')

@app.route('/api/realtime_data')
def realtime_data():
    """API endpoint for current position and analytics."""
    conn = get_db_connection()
    
    # 1. Get latest position
    latest_iss = conn.execute("SELECT * FROM telemetry ORDER BY timestamp_utc DESC LIMIT 1").fetchone()
    
    # 2. Calculate analytics
    analytics = calculate_analytics(conn)
    
    conn.close()
    
    response = {
        'iss': dict(latest_iss) if latest_iss else {},
        'analytics': analytics
    }
    return jsonify(response)

@app.route('/api/path_history')
def path_history():
    """API endpoint for the historical path data (e.g., last 24 hours for the map)."""
    conn = get_db_connection()
    
    # Get all points for the path (limit to last 24 hours for performance)
    one_day_ago = int(time.time()) - (24 * 3600)
    
    path_data = conn.execute("""
        SELECT latitude, longitude, timestamp_utc
        FROM telemetry 
        WHERE timestamp_utc > ? 
        ORDER BY timestamp_utc ASC
    """, (one_day_ago,)).fetchall()
    
    conn.close()
    
    # Format for Leaflet.js [ [lat1, lon1], [lat2, lon2], ... ]
    path_coords = [[row['latitude'], row['longitude']] for row in path_data]
    
    return jsonify({'path': path_coords})

if __name__ == '__main__':
    # Flask runs on 0.0.0.0 so it's accessible externally if needed
    app.run(debug=True, host='0.0.0.0', port=5000)

# To run this script: python app.py
