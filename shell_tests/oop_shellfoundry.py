import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from shell_tests.configs import MainConfig
from shell_tests.helpers.download_files_helper import DownloadFile
from shell_tests.helpers.logger import logger
from shell_tests.run_tests import AutomatedTestsRunner


class Shellfoundry:
    def __init__(self):
        self.root_dir = Path.cwd()

    @staticmethod
    def run_command(command: str):
        logger.info(f"Shellfoundry command is performing {command}")
        command_args = command.split()
        response = subprocess.Popen(
            command_args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if "local" in command:
            add_response = response.communicate(b"\n")
            cmd_stdout = add_response[0]
        else:
            cmd_stdout = response.stdout.read()
        logger.info(f"{command} \n {cmd_stdout}")
        return response

    def get_templates(self):
        """This function provide list of available shells templates.

        Default argument is 'gen2', other option 'gen1', 'layer1', 'all'
        """
        templates = self.run_command("list --all")
        logger.debug(f"shellfoundry list --all\n {templates}")
        templates_list = [item.split(" ")[1] for item in templates if "and up" in item]
        logger.debug(f"Collected templates names\n {templates_list}")
        return templates_list

    def new(
        self,
        shell_name: str = "name_for_test_shell",
        template: Optional[str] = None,
        version: Optional[str] = None,
    ):
        if template is not None and "local" not in template and shell_name == "":
            shell_name = re.sub(r"([/,-])", r"_", template)
            logger.debug(f"Shell name generated on template name {shell_name}")
        create_shell_command = f"shellfoundry new {shell_name}"
        if template is not None:
            create_shell_command = f"{create_shell_command} --template {template}"
            if "local" not in template and version:
                create_shell_command = f"{create_shell_command} --version {version}"
        logger.debug(f"Shellfoundry command prepared for run {create_shell_command}")
        return self.run_command(create_shell_command)

    def pack(self, shell_folder: str):
        os.chdir(shell_folder)
        self.run_command("shellfoundry pack")
        os.chdir(str(self.root_dir))

    def get_path_to_zip(self, shell_name: str) -> Path:
        dist_dir = self.root_dir / shell_name / "dist"
        driver_path = next(dist_dir.glob("*.zip"))
        return driver_path


def _run_tests(test_conf: Path):
    try:
        conf = MainConfig.from_yaml(test_conf)
        report = AutomatedTestsRunner(conf).run()
    finally:
        DownloadFile.remove_downloaded_files()
    logger.info(f"\n\nTest results:\n{report}")
    return report.is_success


def check_shellfoundry_templates(template_path: str, test_conf: Path):
    shell_name = "shell_created_by_test"

    sf = Shellfoundry()
    sf.new(shell_name, template_path)
    sf.pack(shell_name)
    shell_path = sf.get_path_to_zip(shell_name)
    conf_path = Path("shell-from-template.yaml")

    with test_conf.open() as f:
        data = f.read()
    data = data.replace("$shell_path", str(shell_path))
    with conf_path.open("w") as f:
        f.write(data)

    _run_tests(conf_path)
    shutil.rmtree(shell_name)


if __name__ == "__main__":
    _dev_dir = "/home/kirill/Documents/dev/quali"
    _template = f"local:{_dev_dir}/shellfoundry-tosca-networking-template"
    _test_conf = Path(
        f"{_dev_dir}/cloudshell-automation-test-configs/shell-from-template-dummy.yaml"
    )
    check_shellfoundry_templates(_template, _test_conf)
