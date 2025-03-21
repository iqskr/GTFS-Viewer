// Global variables
let map;
let markers = [];
let polylines = [];
let spinner;

// Initialize map - this function will be called by Google Maps API
function initMap() {
    const mapOptions = {
        center: { lat: 45.0, lng: -93.0 },  // Default center
        zoom: 10,
        mapTypeId: google.maps.MapTypeId.ROADMAP
    };
    
    map = new google.maps.Map(document.getElementById('map'), mapOptions);
    
    // Now that map is loaded, initialize the rest of the application
    initApp();
}

// Initialize the rest of the application
function initApp() {
    // Initialize spinner
    spinner = new Spinner({
        lines: 13,
        length: 28,
        width: 14,
        radius: 42,
        scale: 1,
        corners: 1,
        color: '#000',
        fadeColor: 'transparent',
        speed: 1,
        rotate: 0,
        animation: 'spinner-line-fade-quick',
        direction: 1,
        zIndex: 2e9,
        className: 'spinner'
    });
    
    // Initialize date time picker
    $('#datetime-picker').datetimepicker({
        format: 'YYYY-MM-DD HH:mm',
        defaultDate: moment()
    });
    
    // Ensure datetime input has a value
    if (!$('#datetime-input').val()) {
        $('#datetime-input').val(moment().format('YYYY-MM-DD HH:mm'));
        console.log("Set default datetime value:", $('#datetime-input').val());
    }
    
    // Load GTFS datasets
    loadGTFSDatasets();
    
    // Set up event listeners
    setupEventListeners();
}

$(document).ready(function() {
    // If Google Maps API is already loaded, initMap will be called directly
    // Otherwise, it will be called when the API loads
    if (typeof google !== 'undefined' && typeof google.maps !== 'undefined') {
        initMap();
    }
    // Otherwise, wait for the callback
});

// Load GTFS datasets
function loadGTFSDatasets() {
    $.ajax({
        url: '/api/gtfs-folders',
        method: 'GET',
        dataType: 'json',
        success: function(data) {
            console.log('GTFS datasets loaded successfully:', data);
            const select = $('#gtfs-select');
            select.empty();
            select.append('<option value="">Select a dataset...</option>');
            
            if (data && Array.isArray(data)) {
                data.forEach(function(folder) {
                    select.append(`<option value="${folder.id}">${folder.name}</option>`);
                });
                
                if (data.length > 0) {
                    select.prop('disabled', false);
                }
            } else if (data && data.error) {
                console.error('Server returned an error:', data.error);
                alert(`Error: ${data.error}`);
            }
        },
        error: function(jqXHR, textStatus, errorThrown) {
            console.error('Error loading GTFS datasets:', textStatus, errorThrown);
            console.log('Response text:', jqXHR.responseText);
            
            let errorMessage = 'Error loading GTFS datasets. Please try again.';
            if (textStatus === 'parsererror') {
                errorMessage = 'Error parsing server response for datasets.';
                console.log('Parse error. Raw response:', jqXHR.responseText);
            }
            
            alert(errorMessage);
        }
    });
}

// Set up event listeners
function setupEventListeners() {
    $('#gtfs-select').change(function() {
        const folderId = $(this).val();
        if (folderId) {
            loadRoutes(folderId);
        } else {
            $('#route-select').empty();
            $('#route-select').append('<option value="">Select a route...</option>');
            $('#route-select').prop('disabled', true);
            $('#datetime-input').prop('disabled', true);
            $('#view-route-btn').prop('disabled', true);
        }
    });
    
    $('#route-select').change(function() {
        const routeId = $(this).val();
        $('#view-route-btn').prop('disabled', !routeId);
    });
    
    $('#view-route-btn').click(function() {
        console.log("View Route button clicked");
        
        const folderId = $('#gtfs-select').val();
        const routeId = String($('#route-select').val());
        const dateTime = $('#datetime-input').val();
        
        console.log(`Form values - Folder: ${folderId}, Route: ${routeId}, DateTime: ${dateTime}`);
        
        if (folderId && routeId && dateTime) {
            loadRouteDetails(folderId, routeId, dateTime);
        } else {
            console.warn("Missing required fields:", {
                folder: folderId ? "OK" : "Missing",
                route: routeId ? "OK" : "Missing",
                dateTime: dateTime ? "OK" : "Missing"
            });
            alert('Please select a GTFS dataset, route, and date/time.');
        }
    });
    
    // Handle upload form submission
    $('#upload-form').submit(function(e) {
        e.preventDefault();
        
        const fileInput = $('#gtfs-file')[0];
        if (!fileInput.files || fileInput.files.length === 0) {
            alert('Please select a file to upload.');
            return;
        }
        
        const file = fileInput.files[0];
        const formData = new FormData();
        formData.append('file', file);
        
        $.ajax({
            url: '/api/upload',
            method: 'POST',
            data: formData,
            contentType: false,
            processData: false,
            beforeSend: function() {
                // Show loading spinner
                $('#loading-spinner').show();
                spinner.spin(document.getElementById('loading-spinner'));
            },
            success: function(data) {
                // Hide loading spinner
                spinner.stop();
                $('#loading-spinner').hide();
                
                if (data.error) {
                    alert(`Error: ${data.error}`);
                    return;
                }
                
                alert('GTFS data uploaded successfully!');
                
                // Reset form
                $('#upload-form')[0].reset();
                
                // Reload GTFS datasets
                loadGTFSDatasets();
            },
            error: function(err) {
                // Hide loading spinner
                spinner.stop();
                $('#loading-spinner').hide();
                
                console.error('Error uploading GTFS data:', err);
                alert('Error uploading GTFS data. Please try again.');
            }
        });
    });
}

// Load routes for selected GTFS dataset
function loadRoutes(folderId) {
    console.log(`Loading routes for folder: ${folderId}`);
    $.ajax({
        url: '/api/routes',
        method: 'GET',
        data: { folder: folderId },
        dataType: 'json',
        beforeSend: function() {
            $('#route-select').prop('disabled', true);
            $('#route-select').empty();
            $('#route-select').append('<option value="">Loading routes...</option>');
            console.log('Sending request to load routes...');
        },
        success: function(data) {
            console.log('Routes loaded successfully:', data);
            const select = $('#route-select');
            select.empty();
            select.append('<option value="">Select a route...</option>');
            
            if (data && Array.isArray(data) && data.length > 0) {
                console.log(`Received ${data.length} routes from server`);
                data.forEach(function(route) {
                    const routeName = route.route_short_name ? 
                        `${route.route_short_name} - ${route.route_long_name}` : 
                        route.route_long_name;
                    
                    // Ensure route_id is stored as a string to prevent type conversion issues
                    select.append(`<option value="${String(route.route_id)}">${routeName}</option>`);
                });
                
                select.prop('disabled', false);
                $('#datetime-input').prop('disabled', false);
            } else if (data && data.error) {
                console.error('Server returned an error:', data.error);
                alert(`Error: ${data.error}`);
                select.append('<option value="">Error loading routes</option>');
            } else {
                console.log('No routes found or empty response');
                select.append('<option value="">No routes found</option>');
            }
        },
        error: function(jqXHR, textStatus, errorThrown) {
            console.error('Error loading routes:', textStatus, errorThrown);
            console.log('Response text:', jqXHR.responseText);
            
            let errorMessage = 'Error loading routes. Please try again.';
            if (textStatus === 'parsererror') {
                errorMessage = 'Error parsing server response. The server may be returning invalid data.';
                console.log('Parse error. Raw response:', jqXHR.responseText);
                
                // Try to manually parse the response
                try {
                    let data = JSON.parse(jqXHR.responseText);
                    console.log('Manually parsed data:', data);
                    if (data && Array.isArray(data) && data.length > 0) {
                        // If we can parse it, try to continue
                        const select = $('#route-select');
                        select.empty();
                        select.append('<option value="">Select a route...</option>');
                        
                        data.forEach(function(route) {
                            const routeName = route.route_short_name ? 
                                `${route.route_short_name} - ${route.route_long_name}` : 
                                route.route_long_name;
                            
                            // Ensure route_id is stored as a string to prevent type conversion issues
                            select.append(`<option value="${String(route.route_id)}">${routeName}</option>`);
                        });
                        
                        select.prop('disabled', false);
                        $('#datetime-input').prop('disabled', false);
                        return;
                    }
                } catch (e) {
                    console.error('Failed to manually parse response:', e);
                }
            }
            
            alert(errorMessage);
            
            const select = $('#route-select');
            select.empty();
            select.append('<option value="">Select a route...</option>');
            select.prop('disabled', true);
            $('#datetime-input').prop('disabled', true);
        }
    });
}

// Load and display route on map
function loadRouteDetails(folderId, routeId, dateTime) {
    // Ensure route ID is a string
    routeId = String(routeId);
    console.log(`Loading route details - Folder: ${folderId}, Route: ${routeId}, DateTime: ${dateTime}`);
    
    $.ajax({
        url: '/api/route-details',
        method: 'GET',
        dataType: 'json',
        data: { 
            folder: folderId, 
            route_id: routeId, 
            datetime: dateTime 
        },
        beforeSend: function() {
            console.log("Sending route details request to server...");
            // Show loading spinner
            $('#loading-spinner').show();
            spinner.spin(document.getElementById('loading-spinner'));
            
            // Clear previous data
            clearMap();
        },
        success: function(data) {
            // Hide loading spinner
            spinner.stop();
            $('#loading-spinner').hide();
            
            console.log("Received route details response:", data);
            
            if (data.error) {
                console.error("Server returned an error:", data.error);
                alert(`Error: ${data.error}`);
                return;
            }
            
            // Check if we have shape data
            if (!data.shape || data.shape.length === 0) {
                console.warn("No shape data received for this route");
                alert("This route does not have shape data to display on the map.");
                return;
            }
            
            // Check if we have stops data
            if (!data.stops || data.stops.length === 0) {
                console.warn("No stops data received for this route");
            }
            
            // Display route on map
            console.log("Displaying route on map...");
            displayRoute(data);
        },
        error: function(jqXHR, textStatus, errorThrown) {
            // Hide loading spinner
            spinner.stop();
            $('#loading-spinner').hide();
            
            console.error('Error loading route details:', textStatus, errorThrown);
            console.log('Response text:', jqXHR.responseText);
            
            let errorMessage = 'Error loading route details. Please try again.';
            if (textStatus === 'parsererror') {
                errorMessage = 'Error parsing route details from server.';
                console.log('Parse error. Raw response:', jqXHR.responseText);
            }
            
            alert(errorMessage);
        }
    });
}

// Display route on map
function displayRoute(routeData) {
    console.log("Starting to display route on map...");
    
    try {
        // Clear previous data
        clearMap();
        
        // Set route color
        let routeColor = '#0000FF';  // Default blue
        if (routeData.route && routeData.route.route_color) {
            routeColor = `#${routeData.route.route_color}`;
            console.log(`Using route color: ${routeColor}`);
        }
        
        // Draw route shape
        if (routeData.shape && routeData.shape.length > 0) {
            console.log(`Drawing route with ${routeData.shape.length} shape points`);
            
            const shapePath = routeData.shape.map(point => {
                try {
                    return { 
                        lat: parseFloat(point.lat), 
                        lng: parseFloat(point.lng) 
                    };
                } catch (e) {
                    console.error("Error parsing coordinate:", point, e);
                    return null;
                }
            }).filter(point => point !== null);
            
            if (shapePath.length === 0) {
                console.error("No valid shape points to display");
                alert("Could not display route: Invalid coordinate data");
                return;
            }
            
            const polyline = new google.maps.Polyline({
                path: shapePath,
                geodesic: true,
                strokeColor: routeColor,
                strokeOpacity: 1.0,
                strokeWeight: 3
            });
            
            console.log("Adding polyline to map");
            polyline.setMap(map);
            polylines.push(polyline);
            
            // Center map on route
            console.log("Setting map bounds to route");
            const bounds = new google.maps.LatLngBounds();
            shapePath.forEach(point => bounds.extend(point));
            map.fitBounds(bounds);
        } else {
            console.warn("No shape data available to display");
        }
        
        // Add stop markers
        if (routeData.stops && routeData.stops.length > 0) {
            console.log(`Adding ${routeData.stops.length} stop markers`);
            
            routeData.stops.forEach(stop => {
                try {
                    const lat = parseFloat(stop.lat);
                    const lng = parseFloat(stop.lng);
                    
                    if (isNaN(lat) || isNaN(lng)) {
                        console.warn(`Invalid stop coordinates: ${stop.id} - ${stop.name}`, stop);
                        return;
                    }
                    
                    const marker = new google.maps.Marker({
                        position: { lat, lng },
                        map: map,
                        title: stop.name,
                        icon: {
                            path: google.maps.SymbolPath.CIRCLE,
                            scale: 5,
                            fillColor: '#FFFFFF',
                            fillOpacity: 1,
                            strokeColor: '#000000',
                            strokeWeight: 1
                        }
                    });
                    
                    // Add info window
                    const infoWindow = new google.maps.InfoWindow({
                        content: `<div><strong>${stop.name}</strong><br>Stop ID: ${stop.id}</div>`
                    });
                    
                    marker.addListener('click', function() {
                        infoWindow.open(map, marker);
                    });
                    
                    markers.push(marker);
                } catch (e) {
                    console.error(`Error adding stop marker for stop ${stop.id}:`, e);
                }
            });
        } else {
            console.warn("No stops data available to display");
        }
        
        console.log("Route display completed");
    } catch (e) {
        console.error("Error displaying route:", e);
        alert("An error occurred while displaying the route. Check the console for details.");
    }
}

// Clear map elements
function clearMap() {
    // Clear markers
    markers.forEach(marker => marker.setMap(null));
    markers = [];
    
    // Clear polylines
    polylines.forEach(polyline => polyline.setMap(null));
    polylines = [];
}
