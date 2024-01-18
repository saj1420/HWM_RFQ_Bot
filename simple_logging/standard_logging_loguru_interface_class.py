"""

logging guide

"""
import logging
import sys

from loguru import logger

from datetime import datetime
from zoneinfo import ZoneInfo

# logger.remove()


# https://github.com/Delgan/loguru/issues/338
def set_datetime(record):
    current_time = datetime.now(tz=ZoneInfo("Asia/Kolkata"))
    record["extra"]["datetime"] = current_time.strftime("%d %b %Y at %H:%M:%S %Z")


logger.configure(patcher=set_datetime)

logger.add(
    "logfile.log",
    backtrace=False,
    diagnose=False,  # Caution, may leak sensitive data in prod when Tue
    format="{extra[datetime]} | {level} | {message}",
    level="WARNING",
    mode="w",
)


class InterceptHandler(logging.Handler):
    def emit(self, record):
        # Get corresponding Loguru level if it exists.
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message.
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def set_logger():
    logging.basicConfig(handlers=[InterceptHandler()], level=logging.WARNING, force=True)
