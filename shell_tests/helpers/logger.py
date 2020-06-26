import logging
from logging import Logger


def get_logger() -> Logger:
    log_level = logging.DEBUG

    new_logger = logging.getLogger("Automation Tests")
    new_logger.setLevel(log_level)

    file_handler = logging.FileHandler("shell-tests.log", "w")
    file_handler.setLevel(log_level)
    std_handler = logging.StreamHandler()
    std_handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s - %(threadName)s - %(levelname)s - %(message)s"
    )
    std_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    new_logger.addHandler(std_handler)
    new_logger.addHandler(file_handler)

    return new_logger


logger = get_logger()
