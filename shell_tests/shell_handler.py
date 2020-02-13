import os
import zipfile

from shell_tests.helpers import (
    download_file,
    is_url,
    get_resource_model_from_shell_definition,
    call_exit_func_on_exc,
    patch_logging,
)


class ShellHandler(object):
    def __init__(self, cs_handler, name, shell_path, dependencies_path, extra_standards,
                 files_to_store, tests_conf, logger):
        """Handler for the Shell driver.

        :type cs_handler: shell_tests.cs_handler.CloudShellHandler
        :type name: str
        :param str shell_path:
        :param str dependencies_path:
        :type extra_standards: list
        :type files_to_store: dict[str, str]
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
        self.files_to_store = {
            self.download_if_url(src): dst
            for src, dst in files_to_store.items()
        }
        self.model = get_resource_model_from_shell_definition(self.shell_path, logger)

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
            conf.files_to_store,
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
        """Upload all dependencies from zip file to offline PyPI."""
        self.logger.info('Putting dependencies to offline PyPI')

        with zipfile.ZipFile(self.dependencies_path) as zip_file:
            for file_obj in map(zip_file.open, zip_file.filelist):
                package_name = file_obj.name
                with patch_logging(file_obj) as new_file_obj:
                    self.cs_handler.add_file_to_offline_pypi(new_file_obj, package_name)

    def clear_offline_pypi(self):
        """Delete all packages from offline PyPI"""

        self.logger.info('Clearing offline PyPI')
        for file_name in self.cs_handler.get_package_names_from_offline_pypi():
            self.cs_handler.remove_file_from_offline_pypi(file_name)

    def deleting_downloaded_files(self):
        """Delete downloaded files."""
        for path in self.downloaded_files:
            self.logger.info('Deleting the downloaded file {}'.format(path))
            try:
                os.remove(path)
            except OSError as e:
                if 'No such file or directory' not in str(e):
                    raise e

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

    def store_files(self):
        for src, dst in self.files_to_store.items():
            self.logger.debug('Storing file {} to the {}'.format(src, dst))
            self.cs_handler.store_file(dst, src_path=src, force=True)

    @call_exit_func_on_exc
    def __enter__(self):
        self.prepare_shell()
        self.store_files()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.delete_shell()
        return False
