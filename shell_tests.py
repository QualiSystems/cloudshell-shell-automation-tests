import logging

import click

from src.configs import ResourceConfig
from src.report_result import SMTPClient
from src.run_tests import main


def get_logger():
    log_level = logging.INFO

    logger = logging.getLogger('Automation Tests')
    logger.setLevel(log_level)

    handler = logging.StreamHandler()

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    logger.addHandler(handler)

    return logger


@click.command()
@click.argument('config_path')
def run_tests(config_path):
    logger = get_logger()
    conf = ResourceConfig.parse_config_from_yaml(config_path)

    success, result = main(conf, logger)

    if conf.report_conf:
        smtp_client = SMTPClient(conf.report.user, conf.report.password, conf.report.recipients)
        smtp_client.send_tests_result(success, result, conf.shell_path)

    return success, result


if __name__ == '__main__':
    run_tests()
