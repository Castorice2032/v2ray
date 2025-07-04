import logging
import sys
from pathlib import Path

class LoggerManager:
    _loggers = {}
    LOG_DIR = Path(__file__).resolve().parent
    LOG_FILE = LOG_DIR / "project.log"

    @classmethod
    def get_logger(cls, name="v2ray", level=logging.INFO):
        if name in cls._loggers:
            return cls._loggers[name]
        logger = logging.getLogger(name)
        logger.setLevel(level)
        if not logger.handlers:
            # Console handler
            ch = logging.StreamHandler(sys.stdout)
            ch.setLevel(level)
            ch.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s %(name)s: %(message)s'))
            logger.addHandler(ch)
            # File handler
            fh = logging.FileHandler(cls.LOG_FILE, encoding="utf-8")
            fh.setLevel(level)
            fh.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s %(name)s: %(message)s'))
            logger.addHandler(fh)
        logger.propagate = False
        cls._loggers[name] = logger
        return logger

# How to use in other files:
# from logs.log import LoggerManager
# logger = LoggerManager.get_logger(__name__)
# logger.info("Test message")
