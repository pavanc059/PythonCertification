from logging import getLogger, StreamHandler, Formatter
from logging import DEBUG, INFO, WARNING, ERROR, CRITICAL
from logging import FileHandler, basicConfig
import os

# Set up the logger
logger = getLogger(__name__)
logger.setLevel(DEBUG)  # Set the logging level to DEBUG

# Set up the console handler
console_handler = StreamHandler()
console_handler.setLevel(DEBUG)  # Set the logging level to DEBUG
console_handler.setFormatter(Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

# Set up the file handler
log_file = os.path.join(os.path.dirname(__file__), 'library_system.log')
file_handler = FileHandler(log_file)
file_handler.setLevel(DEBUG)  # Set the logging level to DEBUG
file_handler.setFormatter(Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

def print_log_levels():
    """
    Print the available logging levels.
    """
    logger.info("Current logger level:"+ str(logger.level))

print_log_levels()