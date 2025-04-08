import os
import logging

RESTIC_LOG_LEVEL_ENV_KEY = "RESTIC_LOG_LEVEL"

# Configure default logger
logger = logging.getLogger("restic")
logging.basicConfig(level=os.environ.get(RESTIC_LOG_LEVEL_ENV_KEY, "INFO").upper())