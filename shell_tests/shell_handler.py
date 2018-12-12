import os
import zipfile

from cs_handler import CloudShellHandler
from shell_tests.helpers import download_file, is_url


class ShellHandler(object):
    def __init__(self, cs_handler, shell_path, dependencies_path, logger):
        """Handler for the Shell driver.

        :param CloudShellHandler cs_handler:
        :param str shell_path:
        :param str dependencies_path:
        :param logging.Logger logger:
        """
        self.cs_handler = cs_handler
        self._shell_path = shell_path
        self.downloaded_shell_file = False
        self._dependencies_path = dependencies_path
        self.downloaded_dependencies_file = False
        self.logger = logger

    @property
    def shell_path(self):
        if is_url(self._shell_path):
            self.logger.info('Downloading the Shell from {}'.format(self._shell_path))
            self._shell_path = download_file(self._shell_path)
            self.downloaded_shell_file = True
        return self._shell_path

    @property
    def dependencies_path(self):
        if self._dependencies_path and is_url(self._dependencies_path):
            self.logger.info('Downloading the dependencies file from {}'.format(
                self._dependencies_path))
            self._dependencies_path = download_file(self._dependencies_path)
            self.downloaded_dependencies_file = True
        return self._dependencies_path

    def install_shell(self):
        """Install the Shell."""
        self.cs_handler.install_shell(self.shell_path)

    def add_dependencies_to_offline_pypi(self):
        """Upload all dependencies from zip file to offline PyPI"""

        self.logger.info('Putting dependencies to offline PyPI')

        with zipfile.ZipFile(self.dependencies_path) as zip_file:
            for file_obj in map(zip_file.open, zip_file.filelist):
                self.cs_handler.add_file_to_offline_pypi(file_obj, file_obj.name)

    def clear_offline_pypi(self):
        """Delete all packages from offline PyPI"""

        self.logger.info('Clearing offline PyPI')
        for file_name in self.cs_handler.get_package_names_from_offline_pypi():
            self.cs_handler.remove_file_from_offline_pypi(file_name)

    def deleting_downloaded_shell(self):
        """Delete downloaded Shell and dependencies if downloaded"""

        if self.downloaded_shell_file:
            self.logger.debug('Delete a downloaded Shell file')
            os.remove(self.shell_path)
        if self.downloaded_dependencies_file:
            self.logger.debug('Delete a downloaded dependencies file')
            os.remove(self.dependencies_path)

    def prepare_shell(self):
        """Prepare Shell."""
        self.logger.info('Start preparing the Shell')

        if self.dependencies_path:
            self.add_dependencies_to_offline_pypi()

        self.install_shell()

        self.logger.info('The Shell prepared')

    def delete_shell(self):
        """Delete the Shell and clear Offline PyPI."""
        self.logger.info('Start deleting the Shell')

        if self.dependencies_path:
            self.clear_offline_pypi()

        self.deleting_downloaded_shell()

        self.logger.info('The Shell is deleted')

    def __enter__(self):
        self.prepare_shell()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.delete_shell()
        return False
