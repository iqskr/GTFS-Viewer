import os
import pandas as pd
import json
from datetime import datetime, timedelta
import uuid
import zipfile
import shutil

class GTFSViewer:
    """Class to handle GTFS data processing and analysis"""
    
    def __init__(self, base_dir='./data'):
        """Initialize the GTFS Viewer
        
        Args:
            base_dir (str): Base directory for GTFS data
        """
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)
    
    def get_available_folders(self):
        """Get list of available GTFS data folders
        
        Returns:
            list: List of folder paths containing GTFS data
        """
        folders = []
        
        # Check if base directory exists
        if not os.path.exists(self.base_dir):
            print(f"Base directory does not exist: {self.base_dir}")
            return folders
        
        print(f"Scanning base directory: {self.base_dir}")
        
        # List all UUID folders
        for uuid_dir in os.listdir(self.base_dir):
            uuid_path = os.path.join(self.base_dir, uuid_dir)
            if os.path.isdir(uuid_path):
                print(f"Found UUID directory: {uuid_path}")
                # For each UUID folder, list timestamp folders
                for timestamp_dir in os.listdir(uuid_path):
                    timestamp_path = os.path.join(uuid_path, timestamp_dir)
                    if os.path.isdir(timestamp_path):
                        print(f"Checking timestamp directory: {timestamp_path}")
                        # Check if this contains GTFS files
                        if self._is_valid_gtfs(timestamp_path):
                            print(f"Valid GTFS found in: {timestamp_path}")
                            agency_name = self._get_agency_name(timestamp_path)
                            print(f"Agency name: {agency_name}")
                            folders.append({
                                'path': timestamp_path,
                                'id': f"{uuid_dir}/{timestamp_dir}",
                                'name': agency_name or timestamp_dir
                            })
                        else:
                            print(f"Invalid GTFS data in: {timestamp_path}")
        
        print(f"Found {len(folders)} valid GTFS folders")
        return folders
    
    def _is_valid_gtfs(self, folder_path):
        """Check if folder contains valid GTFS data
        
        Args:
            folder_path (str): Path to check
            
        Returns:
            bool: True if folder contains required GTFS files
        """
        required_files = ['routes.txt', 'stops.txt', 'trips.txt', 'stop_times.txt']
        missing_files = []
        
        for file in required_files:
            file_path = os.path.join(folder_path, file)
            if not os.path.exists(file_path):
                missing_files.append(file)
        
        if missing_files:
            print(f"Missing required GTFS files in {folder_path}: {', '.join(missing_files)}")
            return False
        
        print(f"All required GTFS files found in {folder_path}")
        return True
    
    def _get_agency_name(self, folder_path):
        """Get agency name from agency.txt if available
        
        Args:
            folder_path (str): Path to GTFS folder
            
        Returns:
            str: Agency name or None if not available
        """
        agency_file = os.path.join(folder_path, 'agency.txt')
        if os.path.exists(agency_file):
            try:
                agency_df = pd.read_csv(agency_file)
                if 'agency_name' in agency_df.columns and not agency_df.empty:
                    return agency_df.iloc[0]['agency_name']
            except:
                pass
        return None
    
    def get_routes(self, folder_id):
        """Get routes from a specific GTFS dataset
        
        Args:
            folder_id (str): Folder ID in the format uuid/timestamp
            
        Returns:
            list: List of routes with their details
        """
        try:
            print(f"Getting routes for folder_id: {folder_id}")
            try:
                uuid_dir, timestamp_dir = folder_id.split('/')
            except ValueError as e:
                print(f"Invalid folder_id format: {folder_id}, error: {e}")
                return []
                
            folder_path = os.path.join(self.base_dir, uuid_dir, timestamp_dir)
            print(f"Looking for routes in: {folder_path}")
            
            if not os.path.exists(folder_path):
                print(f"Folder path does not exist: {folder_path}")
                return []
            
            routes_file = os.path.join(folder_path, 'routes.txt')
            if not os.path.exists(routes_file):
                print(f"Routes file does not exist: {routes_file}")
                return []
                
            print(f"Reading routes from: {routes_file}")
            routes_df = pd.read_csv(routes_file)
            print(f"Found {len(routes_df)} routes")
            
            # Optional: Join with agency info if available
            agency_file = os.path.join(folder_path, 'agency.txt')
            if os.path.exists(agency_file):
                print(f"Reading agency info from: {agency_file}")
                agency_df = pd.read_csv(agency_file)
                if 'agency_id' in routes_df.columns and 'agency_id' in agency_df.columns:
                    print("Merging routes with agency info")
                    routes_df = pd.merge(routes_df, agency_df, on='agency_id', how='left')
            
            # Handle NaN values to avoid JSON serialization issues
            routes_df = routes_df.fillna('')
            
            # Convert to list of dictionaries, ensuring proper serialization
            routes = []
            for _, row in routes_df.iterrows():
                route_dict = {}
                for col in routes_df.columns:
                    # Convert to string to avoid issues with NaN and int/float serialization
                    route_dict[col] = str(row[col]) if not pd.isna(row[col]) else ""
                routes.append(route_dict)
            
            print(f"Returning {len(routes)} routes")
            return routes
            
        except Exception as e:
            print(f"Error getting routes: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_route_details(self, folder_id, route_id, date_time_str):
        """Get route details including polylines and stops
        
        Args:
            folder_id (str): Folder ID in the format uuid/timestamp
            route_id (str): Route ID to get details for
            date_time_str (str): Date and time string in format YYYY-MM-DD HH:MM
            
        Returns:
            dict: Route details including shape and stops
        """
        try:
            print(f"\nProcessing route details request - Folder: {folder_id}, Route: {route_id}, DateTime: {date_time_str}")
            
            uuid_dir, timestamp_dir = folder_id.split('/')
            folder_path = os.path.join(self.base_dir, uuid_dir, timestamp_dir)
            print(f"Looking in folder path: {folder_path}")
            
            if not os.path.exists(folder_path):
                print(f"Error: Folder path does not exist: {folder_path}")
                return {"error": "Folder not found"}
            
            # Parse datetime
            date_time = datetime.strptime(date_time_str, "%Y-%m-%d %H:%M")
            service_date = date_time.strftime("%Y%m%d")
            time_str = date_time.strftime("%H:%M:%S")
            print(f"Parsed date: {service_date}, time: {time_str}")
            
            # Load required files
            print("Loading GTFS files...")
            routes_file = os.path.join(folder_path, 'routes.txt')
            trips_file = os.path.join(folder_path, 'trips.txt')
            stop_times_file = os.path.join(folder_path, 'stop_times.txt')
            stops_file = os.path.join(folder_path, 'stops.txt')
            
            # Check if files exist
            for file_path in [routes_file, trips_file, stop_times_file, stops_file]:
                if not os.path.exists(file_path):
                    print(f"Error: Required file missing: {file_path}")
                    return {"error": f"Required GTFS file missing: {os.path.basename(file_path)}"}
            
            # Load dataframes
            routes_df = pd.read_csv(routes_file)
            trips_df = pd.read_csv(trips_file)
            stop_times_df = pd.read_csv(stop_times_file)
            stops_df = pd.read_csv(stops_file)
            
            print(f"Loaded {len(routes_df)} routes, {len(trips_df)} trips, {len(stop_times_df)} stop times, {len(stops_df)} stops")
            
            # Filter to the specific route
            # Convert route_id to both string and integer forms for comparison
            # since GTFS data might have inconsistent types between files
            print(f"Filtering trips for route_id: {route_id}")
            
            try:
                route_id_int = int(route_id)
                # Use == comparisons separately and combine with logical OR
                trips_route_id_match = trips_df['route_id'] == route_id
                trips_route_id_int_match = trips_df['route_id'] == route_id_int
                trips_route_id_str_match = trips_df['route_id'].astype(str) == route_id
                
                # Combine the conditions
                route_trips = trips_df[trips_route_id_match | trips_route_id_int_match | trips_route_id_str_match]
            except (ValueError, TypeError):
                # If route_id can't be converted to int, just use string comparison
                trips_route_id_match = trips_df['route_id'] == route_id
                trips_route_id_str_match = trips_df['route_id'].astype(str) == route_id
                
                # Combine the conditions
                route_trips = trips_df[trips_route_id_match | trips_route_id_str_match]
                
            print(f"Found {len(route_trips)} trips for route {route_id}")
            
            if len(route_trips) == 0:
                print(f"No trips found for route ID: {route_id}")
                # Log available route IDs for debugging
                available_route_ids = trips_df['route_id'].unique()
                print(f"Available route IDs in trips.txt: {available_route_ids}")
                return {"error": f"No trips found for route ID: {route_id}. This may be due to a data mismatch between routes.txt and trips.txt, or the route is not active on the selected date."}
            
            # Get service IDs active on the selected date
            service_ids = None
            calendar_file = os.path.join(folder_path, 'calendar.txt')
            calendar_dates_file = os.path.join(folder_path, 'calendar_dates.txt')
            
            # Check calendar.txt for service periods
            if os.path.exists(calendar_file):
                print(f"Loading calendar data from: {calendar_file}")
                calendar_df = pd.read_csv(calendar_file)
                
                # Filter for services where the current date is within the range
                service_date_int = int(service_date)
                
                # Filter for services where the current date is within the range
                start_date_le = calendar_df['start_date'].astype(int) <= service_date_int
                end_date_ge = calendar_df['end_date'].astype(int) >= service_date_int
                valid_services = calendar_df[start_date_le & end_date_ge]
                
                # Further filter by day of week
                weekday = date_time.weekday()
                # In GTFS, Monday is 1 in Python it's 0, etc.
                weekday_mapping = {
                    0: 'monday', 1: 'tuesday', 2: 'wednesday', 
                    3: 'thursday', 4: 'friday', 5: 'saturday', 6: 'sunday'
                }
                weekday_column = weekday_mapping[weekday]
                
                if weekday_column in calendar_df.columns:
                    valid_services = valid_services[valid_services[weekday_column] == 1]
                    
                if not valid_services.empty:
                    service_ids = valid_services['service_id'].unique()
                    print(f"Found {len(service_ids)} valid service IDs for date {service_date}: {service_ids}")
            
            # Check for specific overrides in calendar_dates.txt
            if os.path.exists(calendar_dates_file):
                print(f"Loading calendar dates from: {calendar_dates_file}")
                calendar_dates_df = pd.read_csv(calendar_dates_file)
                
                # Check for service exceptions for the specific date
                if 'date' in calendar_dates_df.columns and 'exception_type' in calendar_dates_df.columns:
                    # Convert service date for proper comparison
                    service_date_int = int(service_date)
                    date_equals = calendar_dates_df['date'].astype(int) == service_date_int
                    date_exceptions = calendar_dates_df[date_equals]
                    
                    if not date_exceptions.empty:
                        # exception_type 1 = service added, 2 = service removed
                        added_services = date_exceptions[date_exceptions['exception_type'] == 1]['service_id'].unique()
                        removed_services = date_exceptions[date_exceptions['exception_type'] == 2]['service_id'].unique()
                        
                        print(f"Service exceptions for {service_date}: Added {len(added_services)}, Removed {len(removed_services)}")
                        
                        # Update service_ids based on exceptions
                        if service_ids is not None:
                            # Remove services that are explicitly removed
                            service_ids = [sid for sid in service_ids if sid not in removed_services]
                            # Add services that are explicitly added
                            service_ids = list(set(service_ids).union(set(added_services)))
                        else:
                            # If no service_ids from calendar.txt, use the added_services
                            service_ids = added_services
            
            # If no service information found, don't filter by service_id
            if service_ids is not None and len(service_ids) > 0:
                print(f"Filtering trips by service IDs: {service_ids}")
                route_trips = route_trips[route_trips['service_id'].isin(service_ids)]
                print(f"After service filtering: Found {len(route_trips)} trips for route {route_id}")
                
                if len(route_trips) == 0:
                    print(f"No trips found for route ID {route_id} on service date {service_date}")
                    return {"error": f"No trips scheduled for route ID {route_id} on {date_time_str}"}
            else:
                print("No valid service IDs found for the selected date, not filtering by service")
            
            # Find trip that is active at the given time
            # This is also simplified - actual implementation would be more complex
            trip_stops = pd.merge(route_trips, stop_times_df, on='trip_id')
            print(f"Found {len(trip_stops)} stop times across all trips for this route")
            
            # Get shape data if available
            shape_points = []
            if 'shape_id' in route_trips.columns:
                # If we have a shapes.txt file, use it to get route shapes
                shapes_file = os.path.join(folder_path, 'shapes.txt')
                if os.path.exists(shapes_file):
                    print(f"Loading shapes from: {shapes_file}")
                    shapes_df = pd.read_csv(shapes_file)
                    print(f"Loaded {len(shapes_df)} shape points")
                    
                    # Get first trip's shape_id
                    if not route_trips.empty and 'shape_id' in route_trips.columns:
                        first_shape_id = route_trips.iloc[0]['shape_id']
                        print(f"Using shape_id: {first_shape_id}")
                        
                        shape_df = shapes_df[shapes_df['shape_id'] == first_shape_id].sort_values('shape_pt_sequence')
                        print(f"Found {len(shape_df)} shape points for this shape_id")
                        
                        for _, row in shape_df.iterrows():
                            shape_points.append({
                                'lat': float(row['shape_pt_lat']),
                                'lng': float(row['shape_pt_lon'])
                            })
                else:
                    print(f"No shapes.txt file found in: {folder_path}")
            else:
                print("No shape_id column in trips data")
            
            print(f"Created {len(shape_points)} shape points for the route")
            
            # Get stops for this route
            stop_ids = trip_stops['stop_id'].unique()
            print(f"Found {len(stop_ids)} unique stop IDs for the route")
            
            route_stops = stops_df[stops_df['stop_id'].isin(stop_ids)]
            print(f"Found {len(route_stops)} stops matching the stop IDs")
            
            stops_list = []
            for _, stop in route_stops.iterrows():
                stops_list.append({
                    'id': str(stop['stop_id']),
                    'name': str(stop['stop_name']) if not pd.isna(stop['stop_name']) else "",
                    'lat': float(stop['stop_lat']),
                    'lng': float(stop['stop_lon'])
                })
            
            # Get route details
            route_info = {}
            if not routes_df[routes_df['route_id'] == route_id].empty:
                route_row = routes_df[routes_df['route_id'] == route_id].iloc[0]
                for col in routes_df.columns:
                    # Convert to string to avoid issues with NaN and int/float serialization
                    route_info[col] = str(route_row[col]) if not pd.isna(route_row[col]) else ""
            
            result = {
                'route': route_info,
                'shape': shape_points,
                'stops': stops_list
            }
            
            print(f"Returning route details: {len(result['shape'])} shape points, {len(result['stops'])} stops")
            return result
            
        except Exception as e:
            print(f"Error getting route details: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}
    
    def upload_gtfs(self, file_obj):
        """Upload and extract a GTFS zip file
        
        Args:
            file_obj: File-like object containing GTFS zip data
            
        Returns:
            str: Folder ID where GTFS was extracted
        """
        try:
            # Create UUID folder
            folder_uuid = str(uuid.uuid4())
            uuid_dir = os.path.join(self.base_dir, folder_uuid)
            print(f"Creating UUID directory: {uuid_dir}")
            os.makedirs(uuid_dir, exist_ok=True)
            
            # Create timestamp subfolder
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            extract_dir = os.path.join(uuid_dir, timestamp)
            print(f"Creating timestamp directory: {extract_dir}")
            os.makedirs(extract_dir, exist_ok=True)
            
            # Save the uploaded file
            zip_path = os.path.join(uuid_dir, 'gtfs.zip')
            print(f"Saving uploaded file to: {zip_path}")
            with open(zip_path, 'wb') as f:
                f.write(file_obj.read())
            
            # Extract the zip file
            print(f"Extracting zip file to: {extract_dir}")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # Clean up the zip file
            print(f"Removing temporary zip file: {zip_path}")
            os.remove(zip_path)
            
            # Verify GTFS data
            if not self._is_valid_gtfs(extract_dir):
                print(f"Extracted data is not valid GTFS: {extract_dir}")
                # Don't delete the folder, keep it for inspection
                # But return an error
                raise ValueError("Uploaded file does not contain valid GTFS data")
            
            folder_id = f"{folder_uuid}/{timestamp}"
            print(f"GTFS data successfully extracted to folder ID: {folder_id}")
            return folder_id
        except Exception as e:
            print(f"Error in upload_gtfs: {e}")
            import traceback
            traceback.print_exc()
            raise
