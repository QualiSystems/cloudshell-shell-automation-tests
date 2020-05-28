from pathlib import Path

import click

from shell_tests.configs import MainConfig
from shell_tests.helpers.cli_helpers import PathPath
from shell_tests.helpers.download_files_helper import DownloadFile
from shell_tests.run_tests import AutomatedTestsRunner


@click.group()
def cli():
    pass


@cli.command("run_tests")
@click.argument("test_conf", type=PathPath(exists=True, dir_okay=False))
def run_tests(test_conf: Path):
    try:
        conf = MainConfig.from_yaml(test_conf)
        report = AutomatedTestsRunner(conf).run()
    finally:
        DownloadFile.remove_downloaded_files()

    print(f"\n\nTest results:\n{report}")  # noqa
    return report.is_success, report


if __name__ == "__main__":
    cli()
