import shutil
import subprocess
import time
import logging
import yaml
import re
import os
from shell_tests.configs import MainConfig
from shell_tests.run_tests import AutomatedTestsRunner

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


class Shellfoundry:

    def __init__(self, logger):
        self.logger = logger
        self.root_dir = os.getcwd()

    # @property
    # def cmd_process(self):
    #     return subprocess.Popen('cmd', stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    #
    # def get_templates(self):
    #     response = self.cmd_process().communicate(f'shellfoundry list\n'.encode())

    def run_command(self, command, add_command = None):

        self.logger.info("Shellfondry command is performing [{}]".format(command))
        response = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if 'local' in command:
            add_response = response.communicate(b'\n')
            cmd_stdout = add_response[0]
        else:
            cmd_stdout = response.stdout.read()

        self.logger.info("{} \n {}".format(command, cmd_stdout))
        return response

    def get_templates(self):
        """This function provide list of available shells templates.
        Default argument is 'gen2', other option 'gen1', 'layer1', 'all' """

        templates = self.run_command('list --all')
        self.logger.debug("shellfondry list --all\n {}".format(templates))

        templates_list = [item.split(' ')[1] for item in templates if 'and up' in item]
        self.logger.debug("Collected templates names\n {}".format(templates_list))

        return templates_list

    def new(self, shell_name = 'name_for_test_shell', template = None, version = None):
        if (template != None and not 'local' in template) and shell_name == '':
            shell_name = re.sub(r'([/,-])', r'_', template)
            self.logger.debug("Shell name generated on template name {}".format(shell_name))

            if version != None:
                create_shell_command = 'shellfoundry new {} --template {} --version {}'.format(shell_name, template, version)
                self.logger.debug("Shellfoundry command prepared for run {}".format(create_shell_command))

            else:
                create_shell_command = 'shellfoundry new {} --template {}'.format(shell_name, template)
                self.logger.debug("Shellfoundry command prepared for run {}".format(create_shell_command))
        elif 'local' in template:
            create_shell_command = 'shellfoundry new {} --template {}'.format(shell_name, template)
            self.logger.debug("Shellfoundry command prepared for run {}".format(create_shell_command))
        else:
            create_shell_command = 'shellfoundry new {}'.format(shell_name)
            self.logger.debug("Shellfoundry command prepared for run {}".format(create_shell_command))

        return self.run_command(create_shell_command)

    def pack(self, shell_folder):
        os.chdir(shell_folder)
        shell_dir = os.getcwd()
        return self.run_command('shellfoundry pack'), shell_dir

    def get_path_to_zip(self):
        os.chdir('dist')
        directory = '{}\{}'.format(os.getcwd(), os.listdir(os.getcwd())[0])
        os.chdir(self.root_dir)
        return directory


def _run_tests(logger, test_conf, env_conf=None):

    conf = MainConfig.parse_from_yaml(test_conf, env_conf)

    report = AutomatedTestsRunner(conf, logger).run()

    print('\n\nTest results:\n{}'.format(report))
    return report.is_success


def check_shellfoundry_templates():

    logger = get_logger()

    shell_name = 'shell_created_by_test'
    template = r'local:c:\Users\dmit\Documents\myprojects\shellfoundry-tosca-networking-template'

    sf = Shellfoundry(logger)
    sf.new(shell_name, template)
    shell_dir = sf.pack(shell_name)

    shell_path = sf.get_path_to_zip()

    conf_path = 'C:\myprojects\cloudshell-shell-automation-tests\shell-from-template.yaml'

    with open('C:\myprojects\cloudshell-shell-automation-tests\shell-from-template-dummy.yaml') as f:
        data = f.read()

    data = data.replace('$shell_path', shell_path)

    with open('C:\myprojects\cloudshell-shell-automation-tests\shell-from-template.yaml', 'w') as f:
        f.write(data)

    _run_tests(logger, conf_path)

    shutil.rmtree(shell_dir[-1])


if __name__ == '__main__':
    check_shellfoundry_templates()



