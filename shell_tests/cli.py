from pathlib import Path

import click

from shell_tests import oop_shellfoundry
from shell_tests.configs import MainConfig
from shell_tests.helpers.cli_helpers import PathPath
from shell_tests.helpers.logger import logger
from shell_tests.prepare_env import AutomatedPrepareEnv
from shell_tests.run_tests import AutomatedTestsRunner


@click.group()
def cli():
    pass


@cli.command("run-tests")
@click.argument("test_conf", type=PathPath(exists=True, dir_okay=False))
def run_tests(test_conf: Path):
    conf = MainConfig.from_yaml(test_conf)
    report = AutomatedTestsRunner(conf).run()
    logger.info(f"\n\nTest results:\n{report}")
    return report.is_success, report


@cli.command("check_shellfoundry_templates")
@click.argument("template_path")
@click.argument("test_conf", type=PathPath(exists=True, dir_okay=False))
def check_shellfoundry_templates(template_path: str, test_conf: Path):
    oop_shellfoundry.check_shellfoundry_templates(template_path, test_conf)


@cli.command("prepare-env")
@click.argument("test_conf", type=PathPath(exists=True, dir_okay=False))
def prepare_env(test_conf: Path):
    conf = MainConfig.from_yaml(test_conf)
    AutomatedPrepareEnv(conf).run()


if __name__ == "__main__":
    import sys

    cli(sys.argv[1:])
