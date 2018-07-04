import logging
import traceback
from StringIO import StringIO

import click

from shell_tests.configs import ShellConfig
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
    file_handler = logging.FileHandler('shell-tests.log')
    file_handler.setLevel(log_level)
    std_handler = logging.StreamHandler()
    std_handler.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    std_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.addHandler(std_handler)
    logger.addHandler(file_handler)

    return logger


def get_log_msg(logger):
    return logger.handlers[0].stream.getvalue()


@cli.command()
@click.argument('shell_conf')
@click.argument('env_conf', required=False)
def run_tests(shell_conf, env_conf=None):
    logger = get_logger()
    conf = ShellConfig.parse_config_from_yaml(shell_conf, env_conf)

    try:
        report = TestsRunner(conf, logger).run()
    except Exception:
        if conf.report:
            error_msg = traceback.format_exc()
            smtp_client = SMTPClient(conf.report.user, conf.report.password, conf.report.recipients)
            smtp_client.send_error(error_msg, conf.shell_name, get_log_msg(logger))

        raise

    if conf.report:
        smtp_client = SMTPClient(conf.report.user, conf.report.password, conf.report.recipients)
        smtp_client.send_tests_result(
            report.is_success, report.get_result(), conf.shell_name, get_log_msg(logger))

    print '\n\nTest results:\n{}'.format(report.get_result())
    return report.is_success, report.get_result()


if __name__ == '__main__':
    cli()
