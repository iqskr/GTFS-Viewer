import os
from flask import Flask, render_template, request, jsonify
from gtfsviewer import GTFSViewer
import json
import numpy as np
import pandas as pd
from datetime import datetime

# Custom JSON encoder to handle numpy types and pandas objects
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, pd.Series):
            return obj.tolist()
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if pd.isna(obj):
            return None
        return super().default(obj)

# Initialize Flask app
app = Flask(__name__)
app.config.from_pyfile('flaskapp.cfg')
app.json_encoder = CustomJSONEncoder  # Use custom JSON encoder

# Initialize GTFS Viewer
gtfs_viewer = GTFSViewer()

# Add CORS headers
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    return response

@app.route('/')
def index():
    """Render the main application page"""
    return render_template('index.html')

# Create a safe_jsonify function that ensures all values are JSON serializable
def safe_jsonify(data):
    """Convert data to JSON safely, handling special types"""
    try:
        # First, clean the data
        cleaned_data = _clean_value(data)
        # Then jsonify it
        return jsonify(cleaned_data)
    except Exception as e:
        print(f"Error serializing data: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Data serialization error: {str(e)}"}), 500

def _clean_value(value):
    """Clean a value to ensure it's JSON serializable"""
    # Special case for arrays/collections when checking isna
    if isinstance(value, (list, np.ndarray, pd.Series, pd.DataFrame)):
        if isinstance(value, (np.ndarray)):
            return value.tolist()
        elif isinstance(value, pd.DataFrame):
            # Convert DataFrame to dict of records
            return value.to_dict('records')
        elif isinstance(value, pd.Series):
            # Convert Series to list, handling any non-serializable types
            return [_clean_value(x) for x in value.tolist()]
        elif isinstance(value, (list, tuple)):
            # Recursively clean list values
            return [_clean_value(x) for x in value]
    
    # Handle scalar values
    if pd.isna(value):
        return None
    elif isinstance(value, (np.integer, np.floating)):
        return float(value) if isinstance(value, np.floating) else int(value)
    elif isinstance(value, np.bool_):
        return bool(value)
    elif isinstance(value, datetime):
        return value.isoformat()
    elif isinstance(value, dict):
        # Recursively clean dictionary values
        return {k: _clean_value(v) for k, v in value.items()}
    else:
        return value

@app.route('/api/gtfs-folders', methods=['GET'])
def get_gtfs_folders():
    """API endpoint to get available GTFS folders"""
    try:
        folders = gtfs_viewer.get_available_folders()
        return safe_jsonify(folders)
    except Exception as e:
        print(f"Error in gtfs-folders endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/routes', methods=['GET'])
def get_routes():
    """API endpoint to get routes for a specific GTFS dataset"""
    folder = request.args.get('folder')
    if not folder:
        return jsonify({"error": "No folder specified"}), 400
    
    try:
        routes = gtfs_viewer.get_routes(folder)
        
        # Debug - print what we're returning
        print(f"Routes data type: {type(routes)}")
        print(f"Number of routes: {len(routes) if isinstance(routes, list) else 'not a list'}")
        
        return safe_jsonify(routes)
    except Exception as e:
        print(f"Error in route endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/route-details', methods=['GET'])
def get_route_details():
    """API endpoint to get route details including polylines and stops"""
    folder = request.args.get('folder')
    route_id = request.args.get('route_id')
    date_time = request.args.get('datetime')
    
    if not all([folder, route_id, date_time]):
        return jsonify({"error": "Missing required parameters"}), 400
    
    try:
        route_details = gtfs_viewer.get_route_details(folder, route_id, date_time)
        return safe_jsonify(route_details)
    except Exception as e:
        print(f"Error in route-details endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload_gtfs():
    """API endpoint to upload GTFS data"""
    print("Received GTFS upload request")
    
    if 'file' not in request.files:
        print("No file provided in the request")
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    if file.filename == '':
        print("Empty filename provided")
        return jsonify({"error": "No file selected"}), 400
    
    if not file.filename.endswith('.zip'):
        print(f"Invalid file format: {file.filename}")
        return jsonify({"error": "File must be a ZIP archive"}), 400
    
    try:
        print(f"Processing GTFS upload: {file.filename}")
        folder_id = gtfs_viewer.upload_gtfs(file)
        print(f"GTFS data extracted to folder: {folder_id}")
        return safe_jsonify({"success": True, "folder_id": folder_id})
    except Exception as e:
        print(f"Error processing GTFS upload: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
