import logging


def setup_logger(log_level=logging.DEBUG):
    # Create a logger
    logger = logging.getLogger("hypothesis_tests")
    logger.setLevel(log_level)

    # Create a console handler and set its log level
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)

    # Create a formatter and add it to the handler
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(formatter)

    # Add the handler to the logger
    logger.addHandler(console_handler)

    return logger
