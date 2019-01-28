import contextlib
import glob
import os
import shutil
import sys
import tarfile
import tempfile
import zipfile
from io import BytesIO

from shell_tests.helpers import download_file, is_url, get_resource_family_and_model


class ShellHandler(object):
    def __init__(self, cs_handler, name, shell_path, dependencies_path, extra_standards, tests_conf,
                 logger):
        """Handler for the Shell driver.

        :type cs_handler: shell_tests.cs_handler.CloudShellHandler
        :type name: str
        :param str shell_path:
        :param str dependencies_path:
        :type extra_standards: list
        :type tests_conf: shell_tests.configs.TestsConfig
        :param logging.Logger logger:
        """
        self.logger = logger
        self.downloaded_files = []
        self.cs_handler = cs_handler
        self.name = name
        self.tests_conf = tests_conf

        self.shell_path = self.download_if_url(shell_path)
        self.dependencies_path = self.download_if_url(dependencies_path)
        self.extra_standards = map(self.download_if_url, extra_standards)
        self.family, self.model = get_resource_family_and_model(self.shell_path, logger)

    @classmethod
    def from_conf(cls, conf, cs_handler, logger):
        """Create Shell Handler from the config.

        :type conf: shell_tests.configs.ShellConfig
        :type cs_handler: shell_tests.cs_handler.CloudShellHandler
        :type logger: logging.Logger
        """
        return cls(
            cs_handler,
            conf.name,
            conf.path,
            conf.dependencies_path,
            conf.extra_standards_paths,
            conf.tests_conf,
            logger,
        )

    def download_if_url(self, path):
        if path and is_url(path):
            self.logger.info('Downloading the file from url {}'.format(path))
            path = download_file(path)
            self.downloaded_files.append(path)

        return path

    def install_shell(self):
        """Install the Shell."""
        self.cs_handler.install_shell(self.shell_path)

    def add_extra_standards(self):
        if not self.extra_standards:
            return

        installed_standards = self.cs_handler.get_tosca_standards()

        for standard_path in self.extra_standards:
            standard_name = os.path.basename(standard_path)

            if standard_name not in installed_standards:
                self.cs_handler.add_cs_standard(standard_path)

    def add_dependencies_to_offline_pypi(self):
        """Upload all dependencies from zip file to offline PyPI"""

        self.logger.info('Putting dependencies to offline PyPI')

        with zipfile.ZipFile(self.dependencies_path) as zip_file:
            for file_obj in map(zip_file.open, zip_file.filelist):

                if 'cloudshell-core' in file_obj.name:
                    with self.patch_cs_core(file_obj) as new_file_obj:
                        self.cs_handler.add_file_to_offline_pypi(new_file_obj, file_obj.name)
                else:
                    self.cs_handler.add_file_to_offline_pypi(file_obj, file_obj.name)

    @contextlib.contextmanager
    def patch_cs_core(self, zip_ext_file):
        """Extract config file from the archive, change log level and pack it back."""
        buffer_ = BytesIO(zip_ext_file.read())
        tar_file = tarfile.open(fileobj=buffer_)
        tmp_dir = tempfile.mkdtemp()

        try:
            tar_file.extractall(tmp_dir)
            dir_path = glob.glob('{}/**'.format(tmp_dir))[0]

            self._rewrite_config_file_with_debug(dir_path)

            file_path = os.path.join(tmp_dir, 'cloudshell-core.tar.gz')
            with tarfile.open(file_path, 'w:gz') as tar_file:
                tar_file.add(dir_path, os.path.basename(dir_path))

            file_obj = open(file_path, 'rb')

            try:
                yield file_obj
            finally:
                file_obj.close()

        finally:
            shutil.rmtree(tmp_dir)

    @staticmethod
    def _rewrite_config_file_with_debug(dir_path):
        """Change log level in config file to DEBUG."""
        config_path = os.path.join(dir_path, 'cloudshell/core/logger/qs_config.ini')

        with open(config_path) as f:
            config_str = f.read()

        config_str = config_str.replace("'INFO'", "'DEBUG'")

        with open(config_path, 'w') as f:
            f.write(config_str)

    def clear_offline_pypi(self):
        """Delete all packages from offline PyPI"""

        self.logger.info('Clearing offline PyPI')
        for file_name in self.cs_handler.get_package_names_from_offline_pypi():
            self.cs_handler.remove_file_from_offline_pypi(file_name)

    def deleting_downloaded_files(self):
        """Delete downloaded files."""
        for path in self.downloaded_files:
            self.logger.info('Deleting the downloaded file {}'.format(path))
            os.remove(path)

    def prepare_shell(self):
        """Prepare Shell."""
        self.logger.info('Start preparing the Shell')

        if self.dependencies_path:
            self.add_dependencies_to_offline_pypi()

        self.add_extra_standards()
        self.install_shell()

        self.logger.info('The Shell prepared')

    def delete_shell(self):
        """Delete the Shell and clear Offline PyPI."""
        self.logger.info('Start deleting the Shell')

        if self.dependencies_path:
            self.clear_offline_pypi()

        self.deleting_downloaded_files()

        self.logger.info('The Shell is deleted')

    def __enter__(self):
        try:
            self.prepare_shell()
        except Exception:
            if self.__exit__(*sys.exc_info()):
                pass
            else:
                raise

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.delete_shell()
        return False
