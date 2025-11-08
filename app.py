from flask import Flask, render_template, jsonify
import sqlite3
import time
from datetime import datetime

app = Flask(__name__)
DATABASE_FILE = "iss_telemetry.db"

def get_db_connection():
    """Utility function to create a database connection."""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row # Allows accessing columns by name
    return conn

def calculate_analytics():
    """Calculates Max/Min values and Altitude change (BONUS)."""
    conn = get_db_connection()
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

    # Query 2: Altitude Change (Latest vs. 1 hour ago)
    # This addresses the bonus requirement to capture altitude change.
    
    latest_record = cursor.execute("SELECT timestamp_utc, altitude FROM telemetry ORDER BY timestamp_utc DESC LIMIT 1").fetchone()
    
    altitude_change_km = "N/A"
    
    if latest_record:
        latest_timestamp = latest_record['timestamp_utc']
        latest_altitude = latest_record['altitude']
        
        # Find the record closest to 3600 seconds (1 hour) ago
        target_time = latest_timestamp - 3600 
        
        past_record = cursor.execute("""
            SELECT altitude
            FROM telemetry
            ORDER BY ABS(timestamp_utc - ?)
            LIMIT 1
        """, (target_time,)).fetchone()
        
        if past_record and latest_altitude:
            past_altitude = past_record['altitude']
            altitude_change_km = latest_altitude - past_altitude
    
    conn.close()
    
    result = dict(analytics) if analytics else {}
    # Format the change to 3 decimal places
    result['altitude_change_km'] = f"{altitude_change_km:+.3f}" if isinstance(altitude_change_km, float) else altitude_change_km
    
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
    analytics = calculate_analytics()
    
    conn.close()
    
    response = {
        'iss': dict(latest_iss) if latest_iss else {},
        'analytics': analytics
    }
    return jsonify(response)

@app.route('/api/path_history')
def path_history():
    """API endpoint for the historical path data (last 12 hours for map visualization)."""
    conn = get_db_connection()
    
    # Use 12 hours of data for map path to keep it manageable
    twelve_hours_ago = int(time.time()) - (12 * 3600)
    
    # Also fetch altitude for the chart placeholder
    history_data = conn.execute("""
        SELECT latitude, longitude, altitude, timestamp_utc
        FROM telemetry 
        WHERE timestamp_utc > ? 
        ORDER BY timestamp_utc ASC
    """, (twelve_hours_ago,)).fetchall()
    
    conn.close()
    
    # Format for Leaflet.js [ [lat1, lon1], [lat2, lon2], ... ]
    path_coords = [[row['latitude'], row['longitude']] for row in history_data]
    
    # Format for chart data
    chart_data = {
        'timestamps': [row['timestamp_utc'] * 1000 for row in history_data], # JS uses milliseconds
        'altitudes': [row['altitude'] for row in history_data]
    }
    
    return jsonify({'path': path_coords, 'chart': chart_data})

# NOTE: Render/Gunicorn ignores this block, but keep it for local testing
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
