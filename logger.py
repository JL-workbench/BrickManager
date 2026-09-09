import logging
from logging.handlers import RotatingFileHandler
from config import LOG_DIR

def setup_logging():
    logger = logging.getLogger()
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    handler = RotatingFileHandler(LOG_DIR / "brickmanager.log", maxBytes=1_000_000,
                                  backupCount=3, encoding="utf-8")
    handler.setFormatter(formatter)
    logger.addHandler(console)
    logger.addHandler(handler)
    return logger
