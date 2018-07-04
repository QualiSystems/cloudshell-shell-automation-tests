import logging

import click

from shell_tests.configs import ShellConfig
from shell_tests.run_tests import TestsRunner


@click.group()
def cli():
    pass


def get_logger():
    log_level = logging.DEBUG

    logger = logging.getLogger('Automation Tests')
    logger.setLevel(log_level)

    file_handler = logging.FileHandler('shell-tests.log', 'w')
    file_handler.setLevel(log_level)
    std_handler = logging.StreamHandler()
    std_handler.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    std_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    logger.addHandler(std_handler)
    logger.addHandler(file_handler)

    return logger


@cli.command()
@click.argument('shell_conf')
@click.argument('env_conf', required=False)
def run_tests(shell_conf, env_conf=None):
    logger = get_logger()
    conf = ShellConfig.parse_config_from_yaml(shell_conf, env_conf)

    report = TestsRunner(conf, logger).run()

    print '\n\nTest results:\n{}'.format(report.get_result())
    return report.is_success, report.get_result()


if __name__ == '__main__':
    cli()
