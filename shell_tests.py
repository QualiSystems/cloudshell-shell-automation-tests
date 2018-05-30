import logging

import click

from src.configs import ResourceConfig
from src.run_tests import main


def get_logger():
    log_level = logging.INFO

    logger = logging.getLogger('Automation Tests')
    logger.setLevel(log_level)

    handler = logging.StreamHandler()

    formater = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formater)

    logger.addHandler(handler)

    return logger


@click.command()
@click.argument('config_path')
def run_tests(config_path):
    logger = get_logger()
    conf = ResourceConfig.parse_config_from_yaml(config_path)
    result = main(conf, logger)
    print result
    return result


if __name__ == '__main__':
    run_tests()
