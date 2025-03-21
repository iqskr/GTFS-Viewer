#!/usr/bin/env python

import logging
import traceback
from flaskapp import app

# Set up logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    try:
        logger.info("Starting GTFS Viewer application")
        app.run(host='0.0.0.0', port=8080, debug=True)
    except Exception as e:
        logger.error(f"Error starting application: {e}")
        traceback.print_exc()
