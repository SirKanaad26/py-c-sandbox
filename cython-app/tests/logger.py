import os
import logging

# Set the log file path
log_path = "./logs.log"

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_path, mode="w")
    ]
)

logger = logging.getLogger("shared_logger")
