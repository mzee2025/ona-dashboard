"""
Flask Web Application for ONA Quality Dashboard
Complete improved version - ready for deployment
"""

from flask import Flask, render_template, jsonify, send_file, request
from flask_cors import CORS
import pandas as pd
import json
import os
import logging
from datetime import datetime
import requests
from ona_quality_dashboard import ONAQualityDashboard
import threading
import time
import pytz

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuration
ONA_API_URL = "https://api.ona.io/api/v1/data/864832"
ONA_API_TOKEN = "9cbc65f1c34ff5a3623cdac41043b788014992c0"
DATA_FILE = "ona_data_export.csv"
DASHBOARD_FILE = "ona_quality_dashboard.html"
CONFIG_FILE = "dashboard_config.json"
REFRESH_INTERVAL = 3600  # 1 hour

# Global variables
last_update_time = None
update_in_progress = False


def load_config():
    """Load dashboard configuration"""
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"Config file {CONFIG_FILE} not found, using defaults")
        return {
            'min_duration': 30,
            'max_duration': 120,
            'start_date': '2025-11-01',
            'required_fields': []
        }


def fetch_ona_data():
    """Fetch latest data from ONA API"""
    global last_update_time, update_in_progress
    
    try:
        update_in_progress = True
        logger.info("Fetching data from ONA API...")
        
        headers = {
            "Authorization": f"Token {ONA_API_TOKEN}"
        }
        
        response = requests.get(ONA_API_URL, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            df = pd.DataFrame(data)
            logger.info(f"Fetched {len(df)} total records from ONA")
            
            # Filter data by start date
            config = load_config()
            start_date_str = config.get('start_date', '2025-11-01')
            
            if '_submission_time' in df.columns:
                df['_submission_time'] = pd.to_datetime(df['_submission_time'])
                START_DATE = pd.to_datetime(start_date_str).tz_localize(pytz.UTC)
                
                original_count = len(df)
                df = df[df['_submission_time'] >= START_DATE]
                filtered_count = original_count - len(df)
                
                if filtered_count > 0:
                    logger.info(f"Filtered out {filtered_count} pilot records before {start_date_str}")
                logger.info(f"Keeping {len(df)} records from {start_date_str} onwards")
            
            # Convert duration from seconds to minutes
            if '_duration' in df.columns:
                df['duration_minutes'] = df['_duration'] / 60
                logger.info("Converted duration from seconds to minutes")
            
            # Split geopoint into lat/lon
            if 'hh_geopoint' in df.columns:
                def split_geopoint(geopoint):
                    if pd.isna(geopoint) or geopoint == '':
                        return None, None
                    try:
                        parts = str(geopoint).split()
                        if len(parts) >= 2:
                            return float(parts[0]), float(parts[1])
                        return None, None
                    except:
                        return None, None
                
                df[['latitude', 'longitude']] = df['hh_geopoint'].apply(
                    lambda x: pd.Series(split_geopoint(x))
                )
                logger.info("Split hh_geopoint into latitude and longitude")
            
            # Save to CSV
            df.to_csv(DATA_FILE, index=False)
            last_update_time = datetime.now()
            logger.info(f"Successfully saved {len(df)} records to {DATA_FILE}")
            return True
        else:
            logger.error(f"Failed to fetch data from ONA: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Error fetching ONA data: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    finally:
        update_in_progress = False


def generate_dashboard():
    """Generate the dashboard HTML"""
    try:
        logger.info("Generating dashboard...")
        config = load_config()
        
        if not os.path.exists(DATA_FILE):
            logger.error(f"Data file {DATA_FILE} not found")
            return False
        
        # Check if data file has records
        df = pd.read_csv(DATA_FILE)
        
        if len(df) == 0:
            logger.warning("No data available (all records filtered)")
            # Create placeholder page
            no_data_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>ONA Dashboard - No Data Yet</title>
                <meta http-equiv="refresh" content="300">
                <style>
                    body { 
                        font-family: 'Arial', sans-serif; 
                        text-align: center; 
                        padding: 50px;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        margin: 0;
                    }
                    .container {
                        background: white;
                        color: #333;
                        padding: 50px;
                        border-radius: 20px;
                        max-width: 800px;
                        margin: 0 auto;
                        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    }
                    h1 { color: #667eea; margin-top: 0; font-size: 2.5em; }
                    .status { font-size: 64px; margin: 30px 0; }
                    .info { 
                        background: #e8f4fd; 
                        padding: 25px; 
                        border-radius: 15px; 
                        margin: 30px 0;
                        text-align: left;
                        line-height: 1.8;
                    }
                    .info p { margin: 12px 0; font-size: 1.1em; }
                    .info strong { color: #667eea; }
                    a { 
                        color: white;
                        background: #667eea;
                        padding: 15px 30px;
                        border-radius: 10px;
                        text-decoration: none;
                        display: inline-block;
                        margin: 15px;
                        font-weight: bold;
                        font-size: 1.1em;
                        transition: all 0.3s;
                    }
                    a:hover { 
                        background: #5568d3; 
                        transform: scale(1.05);
                    }
                    .note { 
                        background: #fff3cd; 
                        color: #856404;
                        padding: 20px;
                        border-radius: 10px;
                        margin: 25px 0;
                        border-left: 5px solid #ffc107;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="status">📊</div>
                    <h1>ONA Quality Dashboard</h1>
                    <h2>Waiting for Data Collection</h2>
                    
                    <div class="info">
                        <p><strong>Dashboard Status:</strong> Active and Ready ✅</p>
                        <p><strong>Start Date:</strong> November 1, 2025</p>
                        <p><strong>Current Records:</strong> 0 (waiting for data)</p>
                        <p><strong>Auto-Refresh:</strong> Every 5 minutes</p>
                    </div>
                    
                    <div class="note">
                        <strong>📌 Note:</strong> The dashboard will automatically populate once data collection 
                        starts. All visualizations will appear as soon as data is available.
                    </div>
                    
                    <p style="font-size: 1.2em; margin: 30px 0;"><strong>What will appear:</strong></p>
                    <p style="text-align: left; padding: 0 30px; line-height: 2;">
                        📊 Surveys by district<br>
                        ⏱️ Interview duration analysis<br>
                        👥 Enumerator performance<br>
                        📍 GPS map of locations<br>
                        📈 Daily trends<br>
                        ✅ Quality metrics
                    </p>
                    
                    <br>
                    <a href="/update">Check for Data Now</a>
                    <a href="/api/status" style="background: #06A77D;">System Status</a>
                </div>
            </body>
            </html>
            """
            with open(DASHBOARD_FILE, 'w') as f:
                f.write(no_data_html)
            logger.info("Created placeholder dashboard for no data")
            return True
        
        # Generate actual dashboard
        dashboard = ONAQualityDashboard(DATA_FILE, config=config)
        dashboard.load_data()
        
        # Get column names
        col_mapping = config.get('column_mapping', {})
        district_col = col_mapping.get('district_column', 'district')
        duration_col = col_mapping.get('duration_column', 'duration_minutes')
        enum_col = col_mapping.get('enumerator_column', 'enumerator_id')
        
        success = dashboard.generate_dashboard(
            output_file=DASHBOARD_FILE,
            title='ONA Data Quality Dashboard',
            district_column=district_col,
            duration_column=duration_col,
            enumerator_column=enum_col,
            lat_column='latitude',
            lon_column='longitude'
        )
        
        if success:
            logger.info("Dashboard generated successfully")
        return success
        
    except Exception as e:
        logger.error(f"Error generating dashboard: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def update_dashboard():
    """Complete dashboard update workflow"""
    logger.info("Starting dashboard update...")
    
    if fetch_ona_data():
        if generate_dashboard():
            logger.info("Dashboard update completed successfully")
            return True
    
    logger.error("Dashboard update failed")
    return False


def auto_refresh_worker():
    """Background worker for auto-refresh"""
    while True:
        try:
            logger.info("Auto-refresh triggered")
            update_dashboard()
            time.sleep(REFRESH_INTERVAL)
        except Exception as e:
            logger.error(f"Error in auto-refresh: {str(e)}")
            time.sleep(60)


@app.route('/')
def index():
    """Serve the main dashboard page"""
    if not os.path.exists(DASHBOARD_FILE):
        if not update_dashboard():
            return """
            <html>
                <head><title>ONA Dashboard - Generating</title></head>
                <body style="font-family: Arial; text-align: center; padding: 50px; background: #f5f5f5;">
                    <h1 style="color: #667eea;">🔄 Dashboard Generating...</h1>
                    <p>Please wait while we fetch and process your data.</p>
                    <p><a href="/" style="color: #667eea;">Refresh this page</a> in a moment.</p>
                </body>
            </html>
            """, 503
    
    try:
        with open(DASHBOARD_FILE, 'r', encoding='utf-8') as f:
            dashboard_html = f.read()
        
        # Add update indicator
        update_info = f"""
        <div style="position: fixed; top: 15px; right: 15px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    color: white; padding: 15px 25px; border-radius: 10px; font-family: Arial; z-index: 9999;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
            <div style="font-weight: bold; font-size: 0.9em;">Last Updated</div>
            <div style="font-size: 1.1em; margin-top: 5px;">
                {last_update_time.strftime('%b %d, %Y %H:%M') if last_update_time else 'Unknown'}
            </div>
            <div style="font-size: 0.8em; margin-top: 5px; opacity: 0.9;">Auto-refreshes hourly</div>
        </div>
        """
        
        dashboard_html = dashboard_html.replace('<body>', f'<body>{update_info}')
        return dashboard_html
        
    except Exception as e:
        logger.error(f"Error serving dashboard: {str(e)}")
        return f"Error loading dashboard: {str(e)}", 500


@app.route('/api/status')
def status():
    """API endpoint for dashboard status"""
    return jsonify({
        'status': 'online',
        'last_update': last_update_time.isoformat() if last_update_time else None,
        'update_in_progress': update_in_progress,
        'data_available': os.path.exists(DATA_FILE),
        'dashboard_available': os.path.exists(DASHBOARD_FILE)
    })


@app.route('/api/update', methods=['POST'])
def trigger_update():
    """Manually trigger dashboard update"""
    if update_in_progress:
        return jsonify({
            'success': False,
            'message': 'Update already in progress'
        }), 409
    
    thread = threading.Thread(target=update_dashboard)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True,
        'message': 'Dashboard update triggered'
    })


@app.route('/update')
def update_page():
    """Manual update page"""
    return """
    <html>
        <head>
            <title>Update ONA Dashboard</title>
            <style>
                body { 
                    font-family: Arial; 
                    padding: 50px; 
                    text-align: center; 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    margin: 0;
                }
                .container { 
                    background: white; 
                    padding: 50px; 
                    border-radius: 20px; 
                    max-width: 700px; 
                    margin: 0 auto;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                }
                h1 { color: #667eea; margin-top: 0; }
                button { 
                    padding: 18px 40px; 
                    font-size: 18px; 
                    cursor: pointer; 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white; 
                    border: none; 
                    border-radius: 10px;
                    margin: 15px;
                    font-weight: bold;
                    transition: all 0.3s;
                }
                button:hover { transform: scale(1.05); box-shadow: 0 5px 15px rgba(0,0,0,0.2); }
                #status { 
                    margin-top: 30px; 
                    padding: 25px; 
                    border-radius: 10px; 
                    font-size: 1.1em;
                }
                .success { background: #d4edda; color: #155724; border-left: 5px solid #28a745; }
                .error { background: #f8d7da; color: #721c24; border-left: 5px solid #dc3545; }
                .info { background: #d1ecf1; color: #0c5460; border-left: 5px solid #17a2b8; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔄 Update Dashboard</h1>
                <p style="font-size: 1.1em; color: #666;">Click to fetch the latest data from ONA and refresh all visualizations.</p>
                <button onclick="updateDashboard()">🔄 Update Now</button>
                <button onclick="goHome()" style="background: #06A77D;">📊 View Dashboard</button>
                <div id="status"></div>
            </div>
            
            <script>
                function updateDashboard() {
                    const statusDiv = document.getElementById('status');
                    statusDiv.className = 'info';
                    statusDiv.innerHTML = '⏳ Updating dashboard... This may take 30-60 seconds.';
                    
                    fetch('/api/update', { method: 'POST' })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                statusDiv.className = 'success';
                                statusDiv.innerHTML = '✅ Dashboard updated successfully! Redirecting...';
                                setTimeout(() => { window.location.href = '/'; }, 2000);
                            } else {
                                statusDiv.className = 'error';
                                statusDiv.innerHTML = '❌ Error: ' + data.message;
                            }
                        })
                        .catch(error => {
                            statusDiv.className = 'error';
                            statusDiv.innerHTML = '❌ Error: ' + error;
                        });
                }
                
                function goHome() {
                    window.location.href = '/';
                }
            </script>
        </body>
    </html>
    """


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})


if __name__ == '__main__':
    logger.info("Starting ONA Dashboard Web Application")
    
    # Initial dashboard generation
    if not os.path.exists(DASHBOARD_FILE):
        logger.info("Dashboard not found, generating initial dashboard...")
        update_dashboard()
    
    # Start auto-refresh worker
    refresh_thread = threading.Thread(target=auto_refresh_worker, daemon=True)
    refresh_thread.start()
    logger.info(f"Auto-refresh enabled (interval: {REFRESH_INTERVAL} seconds)")
    
    # Start Flask app
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"Starting Flask server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
