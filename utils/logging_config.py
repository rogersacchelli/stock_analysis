import logging
import os

# Ensure the logs directory exists
os.makedirs('logs', exist_ok=True)

# Configure logger
logger = logging.getLogger('app_logger')
logger.setLevel(logging.DEBUG)

# File handler
file_handler = logging.FileHandler('logs/app.log')
file_handler.setLevel(logging.DEBUG)

# Formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# Stream handler
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)
stream_handler.setFormatter(formatter)

# Add handlers
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# Avoid duplicate logs
logger.propagate = False
