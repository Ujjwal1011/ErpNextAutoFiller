import logging
import os
import sys
from logging.handlers import RotatingFileHandler

# Determine bench root by walking up from this file: utils -> kgmaccount -> kgmaccount -> apps -> frappe-bench
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOGS_DIR, "whatsapp_suitee.log")

_logger = logging.getLogger("kgmaccount")

if not any(hasattr(h, 'baseFilename') and os.path.abspath(h.baseFilename) == os.path.abspath(LOG_FILE) for h in _logger.handlers):
    handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    handler.setFormatter(fmt)
    _logger.addHandler(handler)
    _logger.setLevel(logging.DEBUG)

# Also add a console StreamHandler so logs print directly to stdout
if not any(isinstance(h, logging.StreamHandler) for h in _logger.handlers):
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(fmt)
    stream_handler.setLevel(logging.DEBUG)
    _logger.addHandler(stream_handler)

# expose the configured logger
def get_logger(name=None):
    if name:
        return logging.getLogger(name)
    return _logger
