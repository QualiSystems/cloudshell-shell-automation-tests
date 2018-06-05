import logging
import traceback
from StringIO import StringIO

import click

from shell_tests.configs import ResourceConfig
from shell_tests.report_result import SMTPClient
from shell_tests.run_tests import TestsRunner


@click.group()
def cli():
    pass


def get_logger():
    log_level = logging.DEBUG
    stream = StringIO()

    logger = logging.getLogger('Automation Tests')
    logger.setLevel(log_level)

    handler = logging.StreamHandler(stream)
    std_handler = logging.StreamHandler()

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.addHandler(std_handler)

    return logger


def get_log_msg(logger):
    return logger.handlers[0].stream.getvalue()


@cli.command()
@click.argument('config_path')
def run_tests(config_path):
    logger = get_logger()
    conf = ResourceConfig.parse_config_from_yaml(config_path)

    try:
        is_success, result = TestsRunner(conf, logger).run()
    except Exception:
        if conf.report:
            error_msg = traceback.format_exc()
            smtp_client = SMTPClient(conf.report.user, conf.report.password, conf.report.recipients)
            smtp_client.send_error(error_msg, conf.shell_path, get_log_msg(logger))

        raise

    if conf.report:
        smtp_client = SMTPClient(conf.report.user, conf.report.password, conf.report.recipients)
        smtp_client.send_tests_result(is_success, result, conf.shell_path, get_log_msg(logger))

    return is_success, result


if __name__ == '__main__':
    cli()
