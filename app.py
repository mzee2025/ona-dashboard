"""
Flask Web Application for ONA Quality Dashboard
Complete version with all fixes:
- Timezone-aware date filtering
- GPS geopoint splitting
- Duration conversion (seconds to minutes)
- Correct column mapping
- Enumerator error tracking
- Empty data handling
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
    """Fetch latest data from ONA API with all fixes"""
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
            
            # Filter data by start date (exclude pilot data)
            config = load_config()
            start_date_str = config.get('start_date', '2025-11-01')
            
            if '_submission_time' in df.columns:
                # Convert submission time to datetime
                df['_submission_time'] = pd.to_datetime(df['_submission_time'])
                
                # Make START_DATE timezone-aware to match ONA data (UTC)
                START_DATE = pd.to_datetime(start_date_str).tz_localize(pytz.UTC)
                
                # Filter out pilot data
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
            
            # Split geopoint into separate lat/lon columns
            if 'hh_geopoint' in df.columns:
                def split_geopoint(geopoint):
                    """Split geopoint string into lat, lon"""
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
        
        # Check if data file has any records
        df = pd.read_csv(DATA_FILE)
        
        if len(df) == 0:
            logger.warning("No data available (all records filtered)")
            # Create placeholder page for no data
            no_data_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>ONA Dashboard - No Data Yet</title>
                <meta http-equiv="refresh" content="300">
                <style>
                    body { 
                        font-family: Arial, sans-serif; 
                        text-align: center; 
                        padding: 50px;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        margin: 0;
                    }
                    .container {
                        background: white;
                        color: #333;
                        padding: 40px;
                        border-radius: 20px;
                        max-width: 700px;
                        margin: 0 auto;
                        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    }
                    h1 { color: #667eea; margin-top: 0; }
                    .status { font-size: 64px; margin: 20px 0; }
                    .info { 
                        background: #e8f4fd; 
                        padding: 20px; 
                        border-radius: 10px; 
                        margin: 20px 0;
                        text-align: left;
                    }
                    .info p { margin: 10px 0; }
                    .info strong { color: #667eea; }
                    a { 
                        color: white;
                        background: #667eea;
                        padding: 12px 24px;
                        border-radius: 8px;
                        text-decoration: none;
                        display: inline-block;
                        margin: 10px;
                        font-weight: bold;
                    }
                    a:hover { background: #5568d3; }
                    .note { 
                        background: #fff3cd; 
                        color: #856404;
                        padding: 15px;
                        border-radius: 8px;
                        margin: 20px 0;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="status">📊</div>
                    <h1>ONA Quality Dashboard</h1>
                    <h2>Waiting for Data Collection to Start</h2>
                    
                    <div class="info">
                        <p><strong>Dashboard Status:</strong> Active and Ready ✅</p>
                        <p><strong>Start Date:</strong> November 1, 2025</p>
                        <p><strong>Pilot Records Filtered:</strong> 65 records (before Nov 1)</p>
                        <p><strong>Current Records:</strong> 0 (waiting for Nov 1+ data)</p>
                        <p><strong>Auto-Refresh:</strong> Every 5 minutes</p>
                    </div>
                    
                    <div class="note">
                        <strong>📌 Note:</strong> The dashboard will automatically populate once data collection 
                        starts on November 1, 2025. All pilot data from before this date has been excluded.
                    </div>
                    
                    <p><strong>What will appear once data is available:</strong></p>
                    <p style="text-align: left; padding: 0 20px;">
                        ✅ Completion rates by district<br>
                        ✅ GPS map of interview locations<br>
                        ✅ Duration analysis (in minutes)<br>
                        ✅ Enumerator performance tracking<br>
                        ✅ Data quality metrics
                    </p>
                    
                    <br>
                    <a href="/update">Check for New Data Now</a>
                    <a href="/api/status" style="background: #06A77D;">View System Status</a>
                </div>
            </body>
            </html>
            """
            with open(DASHBOARD_FILE, 'w') as f:
                f.write(no_data_html)
            logger.info("Created placeholder dashboard for no data")
            return True
        
        # Generate actual dashboard with data
        dashboard = ONAQualityDashboard(DATA_FILE, config=config)
        
        # Get column names from config
        col_mapping = config.get('column_mapping', {})
        district_col = col_mapping.get('district_column', 'district')
        duration_col = col_mapping.get('duration_column', 'duration_minutes')
        enum_col = col_mapping.get('enumerator_column', 'enumerator_id')
        
        dashboard.generate_dashboard(
            output_file=DASHBOARD_FILE,
            district_column=district_col,
            duration_column=duration_col,
            lat_column='latitude',
            lon_column='longitude',
            enumerator_column=enum_col
        )
        
        logger.info("Dashboard generated successfully")
        return True
        
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
                <head><title>ONA Dashboard - Error</title></head>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1>Dashboard Not Available</h1>
                    <p>Unable to generate dashboard. Please check logs.</p>
                    <p><a href="/update">Try updating</a></p>
                </body>
            </html>
            """, 500
    
    try:
        with open(DASHBOARD_FILE, 'r', encoding='utf-8') as f:
            dashboard_html = f.read()
        
        # Add update indicator
        update_info = f"""
        <div style="position: fixed; top: 10px; right: 10px; background: #2E86AB; color: white; 
                    padding: 10px 20px; border-radius: 5px; font-family: Arial; z-index: 9999;">
            Last Updated: {last_update_time.strftime('%Y-%m-%d %H:%M:%S') if last_update_time else 'Unknown'}
            <br><small>Auto-refreshes every hour</small>
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
                body { font-family: Arial; padding: 50px; text-align: center; background: #f5f5f5; }
                .container { background: white; padding: 40px; border-radius: 10px; max-width: 600px; margin: 0 auto; }
                h1 { color: #667eea; }
                button { 
                    padding: 15px 30px; 
                    font-size: 18px; 
                    cursor: pointer; 
                    background: #667eea; 
                    color: white; 
                    border: none; 
                    border-radius: 5px;
                    margin: 10px;
                }
                button:hover { background: #5568d3; }
                #status { margin-top: 20px; padding: 20px; border-radius: 5px; }
                .success { background: #d4edda; color: #155724; }
                .error { background: #f8d7da; color: #721c24; }
                .info { background: #d1ecf1; color: #0c5460; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔄 ONA Quality Dashboard</h1>
                <p>Click the button below to fetch the latest data from ONA and refresh the dashboard.</p>
                <button onclick="updateDashboard()">Update Dashboard Now</button>
                <button onclick="goHome()" style="background: #06A77D;">View Dashboard</button>
                <div id="status"></div>
            </div>
            
            <script>
                function updateDashboard() {
                    const statusDiv = document.getElementById('status');
                    statusDiv.className = 'info';
                    statusDiv.innerHTML = '⏳ Updating dashboard... Please wait.';
                    
                    fetch('/api/update', { method: 'POST' })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                statusDiv.className = 'success';
                                statusDiv.innerHTML = '✅ Dashboard update triggered! Redirecting...';
                                setTimeout(() => { window.location.href = '/'; }, 3000);
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


@app.route('/download/report')
def download_report():
    """Download quality report"""
    try:
        report_file = 'quality_report.xlsx'
        
        if not os.path.exists(report_file):
            config = load_config()
            dashboard = ONAQualityDashboard(DATA_FILE, config=config)
            dashboard.export_quality_report(report_file)
        
        return send_file(report_file, as_attachment=True)
        
    except Exception as e:
        logger.error(f"Error downloading report: {str(e)}")
        return f"Error generating report: {str(e)}", 500


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
    
    # Start Flask app (port 8080 to avoid Mac AirPlay on 5000)
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting Flask server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
