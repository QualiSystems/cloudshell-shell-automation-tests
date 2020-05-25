import logging

import click

from shell_tests.configs import MainConfig
from shell_tests.run_tests import AutomatedTestsRunner
from shell_tests import oop_shellfoundry


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

    formatter = logging.Formatter('%(asctime)s - %(threadName)s - %(levelname)s - %(message)s')
    std_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    logger.addHandler(std_handler)
    logger.addHandler(file_handler)

    return logger


@cli.command('run_tests')
@click.argument('test_conf')
@click.argument('env_conf', required=False)
def run_tests(test_conf, env_conf=None):
    logger = get_logger()
    conf = MainConfig.parse_from_yaml(test_conf, env_conf)

    report = AutomatedTestsRunner(conf, logger).run()

    print('\n\nTest results:\n{}'.format(report))
    return report.is_success, report


@cli.command('check_shellfoundry_templates')
@click.argument('template_path')
@click.argument('test_conf')
def check_shellfoundry_templates(template_path, test_conf):
    logger = get_logger()

    oop_shellfoundry.check_shellfoundry_templates(logger, template_path, test_conf)


if __name__ == '__main__':
    import sys
    cli(sys.argv[1:])
