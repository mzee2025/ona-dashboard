"""
Flask Web Application for ONA Quality Dashboard
Serves the dashboard online and provides auto-refresh functionality
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

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration
ONA_API_URL = "https://api.ona.io/api/v1/data/864832"
ONA_API_TOKEN = "9cbc65f1c34ff5a3623cdac41043b788014992c0"
DATA_FILE = "ona_data_export.csv"
DASHBOARD_FILE = "ona_quality_dashboard.html"
CONFIG_FILE = "dashboard_config.json"
REFRESH_INTERVAL = 1800  # 30 minutes in seconds

# Global variables to track update status
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
            'required_fields': ['respondent_name', 'district', 'survey_complete']
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
            df.to_csv(DATA_FILE, index=False)
            last_update_time = datetime.now()
            logger.info(f"Successfully fetched {len(df)} records from ONA")
            return True
        else:
            logger.error(f"Failed to fetch data from ONA: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Error fetching ONA data: {str(e)}")
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
        
        dashboard = ONAQualityDashboard(DATA_FILE, config=config)
        dashboard.generate_dashboard(
            output_file=DASHBOARD_FILE,
            district_column='district',
            duration_column='duration_minutes',
            lat_column='latitude',
            lon_column='longitude'
        )
        
        logger.info("Dashboard generated successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error generating dashboard: {str(e)}")
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
    """Background worker to auto-refresh dashboard"""
    while True:
        try:
            logger.info("Auto-refresh triggered")
            update_dashboard()
            time.sleep(REFRESH_INTERVAL)
        except Exception as e:
            logger.error(f"Error in auto-refresh worker: {str(e)}")
            time.sleep(60)  # Wait 1 minute before retrying


@app.route('/')
def index():
    """Serve the main dashboard page"""
    if not os.path.exists(DASHBOARD_FILE):
        # Generate dashboard if it doesn't exist
        if not update_dashboard():
            return """
            <html>
                <head><title>ONA Dashboard - Error</title></head>
                <body>
                    <h1>Dashboard Not Available</h1>
                    <p>Unable to generate dashboard. Please check logs for details.</p>
                    <p><a href="/update">Click here to try updating</a></p>
                </body>
            </html>
            """, 500
    
    try:
        with open(DASHBOARD_FILE, 'r', encoding='utf-8') as f:
            dashboard_html = f.read()
        
        # Add auto-refresh meta tag and update indicator
        refresh_tag = f'<meta http-equiv="refresh" content="{REFRESH_INTERVAL}">'
        update_info = f"""
        <div style="position: fixed; top: 10px; right: 10px; background: #2E86AB; color: white; 
                    padding: 10px 20px; border-radius: 5px; font-family: Arial; z-index: 9999;">
            Last Updated: {last_update_time.strftime('%Y-%m-%d %H:%M:%S') if last_update_time else 'Unknown'}
            <br><small>Auto-refreshes every hour</small>
        </div>
        """
        
        # Insert into HTML
        dashboard_html = dashboard_html.replace('</head>', f'{refresh_tag}</head>')
        dashboard_html = dashboard_html.replace('<body>', f'<body>{update_info}')
        
        return dashboard_html
        
    except Exception as e:
        logger.error(f"Error serving dashboard: {str(e)}")
        return f"Error loading dashboard: {str(e)}", 500


@app.route('/api/status')
def status():
    """API endpoint to check dashboard status"""
    return jsonify({
        'status': 'online',
        'last_update': last_update_time.isoformat() if last_update_time else None,
        'update_in_progress': update_in_progress,
        'data_available': os.path.exists(DATA_FILE),
        'dashboard_available': os.path.exists(DASHBOARD_FILE)
    })


@app.route('/api/update', methods=['POST'])
def trigger_update():
    """API endpoint to manually trigger dashboard update"""
    if update_in_progress:
        return jsonify({
            'success': False,
            'message': 'Update already in progress'
        }), 409
    
    # Run update in background thread
    thread = threading.Thread(target=update_dashboard)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True,
        'message': 'Dashboard update triggered'
    })


@app.route('/update')
def update_page():
    """Manual update trigger page"""
    return """
    <html>
        <head>
            <title>Update ONA Dashboard</title>
            <style>
                body { font-family: Arial; padding: 50px; text-align: center; }
                button { padding: 15px 30px; font-size: 18px; cursor: pointer; 
                        background: #2E86AB; color: white; border: none; border-radius: 5px; }
                button:hover { background: #1a5f7a; }
                #status { margin-top: 20px; padding: 20px; border-radius: 5px; }
                .success { background: #d4edda; color: #155724; }
                .error { background: #f8d7da; color: #721c24; }
                .info { background: #d1ecf1; color: #0c5460; }
            </style>
        </head>
        <body>
            <h1>ONA Quality Dashboard</h1>
            <p>Click the button below to manually update the dashboard with latest data from ONA.</p>
            <button onclick="updateDashboard()">Update Dashboard Now</button>
            <div id="status"></div>
            
            <script>
                function updateDashboard() {
                    const statusDiv = document.getElementById('status');
                    statusDiv.className = 'info';
                    statusDiv.innerHTML = 'Updating dashboard... Please wait.';
                    
                    fetch('/api/update', { method: 'POST' })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                statusDiv.className = 'success';
                                statusDiv.innerHTML = 'Dashboard update triggered! Redirecting to dashboard...';
                                setTimeout(() => { window.location.href = '/'; }, 3000);
                            } else {
                                statusDiv.className = 'error';
                                statusDiv.innerHTML = 'Error: ' + data.message;
                            }
                        })
                        .catch(error => {
                            statusDiv.className = 'error';
                            statusDiv.innerHTML = 'Error updating dashboard: ' + error;
                        });
                }
            </script>
        </body>
    </html>
    """


@app.route('/api/metrics')
def metrics():
    """API endpoint to get current metrics as JSON"""
    try:
        if not os.path.exists(DATA_FILE):
            return jsonify({'error': 'No data available'}), 404
        
        config = load_config()
        dashboard = ONAQualityDashboard(DATA_FILE, config=config)
        
        completion_rates = dashboard.calculate_completion_rates('district')
        missing_data = dashboard.analyze_missing_data()
        duration_flags = dashboard.flag_interview_durations('duration_minutes')
        
        return jsonify({
            'total_records': len(dashboard.data),
            'last_update': last_update_time.isoformat() if last_update_time else None,
            'completion_rate': float(completion_rates['completion_rate'].mean()) if not completion_rates.empty else None,
            'duration_flags': len(duration_flags),
            'missing_data_fields': len(missing_data),
            'districts': completion_rates.to_dict('records') if not completion_rates.empty else []
        })
        
    except Exception as e:
        logger.error(f"Error getting metrics: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/download/report')
def download_report():
    """Download the quality report Excel file"""
    try:
        report_file = 'quality_report.xlsx'
        
        if not os.path.exists(report_file):
            # Generate report if it doesn't exist
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
    # Initial dashboard generation
    logger.info("Starting ONA Dashboard Web Application")
    
    # Try to fetch data and generate dashboard on startup
    if not os.path.exists(DASHBOARD_FILE):
        logger.info("Dashboard not found, generating initial dashboard...")
        update_dashboard()
    
    # Start auto-refresh worker in background
    refresh_thread = threading.Thread(target=auto_refresh_worker, daemon=True)
    refresh_thread.start()
    logger.info(f"Auto-refresh enabled (interval: {REFRESH_INTERVAL} seconds)")
    
    # Start Flask app
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting Flask server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
