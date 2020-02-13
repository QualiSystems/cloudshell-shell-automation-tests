import glob
import io
import itertools
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import urllib2
import urlparse
import zipfile
from collections import defaultdict
from contextlib import closing
from functools import wraps
from io import BytesIO
from xml.etree import ElementTree

import xmltodict
import yaml
from contextlib2 import ExitStack

DOWNLOAD_FOLDER = 'shell_tests'


def get_resource_model_from_shell_definition(shell_path, logger):
    """Get resource family and model from shell-definition.yaml

    :param str shell_path: path to Shell zip
    :param logging.Logger logger:
    :return: family and model
    :rtype: tuple[str, str]"""

    with zipfile.ZipFile(shell_path) as zip_file:
        data = yaml.safe_load(zip_file.read('shell-definition.yaml'))

    model = data['node_types'].keys()[0].rsplit('.', 1)[-1]
    logger.debug('Model: {} for the Shell {}'.format(model, shell_path))
    return model


def download_file(url, folder_path=None):
    """Download a file to the tmp folder

    :param str url: can be http or ftp link
    :param str folder_path:
    :return: file_path
    :rtype: str
    """

    file_name = url.rsplit('/', 1)[-1]

    if folder_path is None:
        folder_path = os.path.join(tempfile.gettempdir(), DOWNLOAD_FOLDER)
        if not os.path.exists(folder_path):
            os.mkdir(folder_path)

    file_path = os.path.join(folder_path, file_name)
    with closing(urllib2.urlopen(url)) as data, open(file_path, 'wb') as file_obj:
        file_obj.write(data.read())

    return file_path


def is_url(url):
    return urlparse.urlparse(url).scheme in ('http', 'https', 'ftp', 'ftps', 'tftp')


def get_file_name_from_url(url):
    return os.path.basename(urlparse.urlparse(url).path)


def is_host_alive(host):
    ping_count_str = 'n' if platform.system().lower() == 'windows' else 'c'
    cmd = 'ping -{} 1 {}'.format(ping_count_str, host)

    try:
        _ = subprocess.check_output(cmd, shell=True)
    except subprocess.CalledProcessError:
        return False

    return True


def get_driver_metadata(shell_path):
    with zipfile.ZipFile(shell_path) as zip_file:

        driver_name = re.search(r'\'(\S+\.zip)\'', str(zip_file.namelist())).group(1)
        driver_file = io.BytesIO(zip_file.read(driver_name))

        with zipfile.ZipFile(driver_file) as driver_zip:
            driver_metadata = driver_zip.read('drivermetadata.xml')

    return driver_metadata


def get_driver_commands(shell_path):
    """Get commands from the drivermetadata.xml.

    :type shell_path: str
    :rtype: list[str]
    """
    driver_metadata = get_driver_metadata(shell_path)

    doc = ElementTree.fromstring(driver_metadata)
    commands = doc.findall('Layout/Category/Command')
    commands.extend(doc.findall('Layout/Command'))

    return [command.get('Name') for command in commands]


def merge_dicts(first, second):
    """Create a new dict from two dicts, first replaced second.

    :param dict first:
    :param dict second:
    :rtype: dict
    """
    new_dict = second.copy()

    for key, val in first.iteritems():
        if isinstance(val, dict):
            new_dict[key] = merge_dicts(val, new_dict.get(key, {}))
        elif isinstance(val, list):
            lst = second.get(key, [])[:]
            lst.extend(val)
            new_dict[key] = lst
        else:
            new_dict[key] = val

    return new_dict


def wait_for_end_threads(threads):
    """Endless loop that wait for ending the threads.

    :type threads: list[threading.Thread]
    """
    while any(map(threading.Thread.is_alive, threads)):
        time.sleep(1)


class enter_stacks(object):
    def __init__(self, stacks):
        self.stacks = stacks
        self.main_stack = ExitStack()

    def __enter__(self):
        self.main_stack.__enter__()
        map(self.main_stack.enter_context, self.stacks)

    def __exit__(self, *args):
        self.main_stack.__exit__(*args)


def call_exit_func_on_exc(enter_fn):
    @wraps(enter_fn)
    def wrapper(self):
        try:
            return enter_fn(self)
        except Exception:
            if self.__exit__(*sys.exc_info()):
                pass
            else:
                raise
    return wrapper


class cached_property(object):
    """A property that is only computed once per instance and then replaces
       itself with an ordinary attribute. Deleting the attribute resets the
       property.

       Source: https://github.com/bottlepy/bottle/blob/0.11.5/bottle.py#L175
    """

    def __init__(self, func):
        self.__doc__ = getattr(func, '__doc__')
        self.func = func

    def __get__(self, obj, cls):
        if obj is None:
            # We're being accessed from the class itself, not from an object
            return self
        value = obj.__dict__[self.func.__name__] = self.func(obj)
        return value


def get_str_connections_form_blueprint(path, bp_name):
    """Get a list of connections in the blueprint.

    :param path: path to a package zip file
    :type path: str
    :param bp_name: name of the Blueprint
    :type bp_name: str
    :rtype: tuple[tuple[str, str], tuple[str, str]]
    :return: (first_resource_name, requested_port_names), (second_resource_name, requested_port_names)
    """
    xml_name = '{}.xml'.format(bp_name)
    xml_path = 'Topologies/{}'.format(xml_name)

    with zipfile.ZipFile(path) as zip_file:
        xml_data = zip_file.read(xml_path)

    data = xmltodict.parse(xml_data)
    source_ports = target_ports = 'any'

    connector = data['TopologyInfo']['Routes']['Connector']
    source_name = connector['@Source']
    target_name = connector['@Target']

    for attribute in connector.get('Attributes', {}).get('Attribute', []):
        if attribute['@Name'] == 'Requested Target vNIC Name':
            target_ports = attribute['@Value']
        elif attribute['@Name'] == 'Requested Source vNIC Name':
            source_ports = attribute['@Value']

    return source_name, source_ports, target_name, target_ports


def parse_connections(source_name, source_ports, target_name, target_ports):
    """Parse ports from blueprint.

    :param str source_name: blueprint resource name
    :param str source_ports: requested ports to connect, "2,3", "", ...
    :param str target_name: blueprint resource name
    :param str target_ports: requested ports to connect, "3,2", "", ...
    :rtype: dict[tuple[str, str], list[tuple[str, str]]]
    :return:
        {
            (first_resource, requested_port_name): [(second_resource, requested_port_name)]
        }
    """
    connections = defaultdict(list)

    target_ports = target_ports.split(',')
    source_ports = source_ports.split(',')

    for source_port, target_port in itertools.izip_longest(source_ports, target_ports, fillvalue='any'):
        connections[(source_name, source_port)].append((target_name, target_port))

    return connections


class patch_logging(object):
    """Change log level to DEBUG in cloudshell-core and cloudshell-logging.

    :type zip_ext_file: zipfile.ZipExtFile
    """

    FILE_PATTERN = re.compile(
        r'^(cloudshell[-_]core|cloudshell[-_]logging)-(\d+\.?)+'
        r'(-\w+(\.\w+)?-\w+-\w+)?'
        r'\.(tar\.gz|zip|whl)$'
    )

    def __init__(self, zip_ext_file):
        self._zip_ext_file = zip_ext_file
        self._tmp_dir = None
        self._archive_obj = None

    def _extract_archive(self, buffer_, ext):
        """Extract the archive to tmp dir and returns path to extracted dir.

        :type buffer_: BytesIO
        :type ext: str
        :rtype: str
        """
        if ext in ('zip', 'whl'):
            arch_file = zipfile.ZipFile(buffer_)
        elif ext == 'tar.gz':
            arch_file = tarfile.open(fileobj=buffer_)
        else:
            raise ValueError('Unsupported extension')

        if self._tmp_dir is None:
            self._tmp_dir = tempfile.mkdtemp()
        arch_file.extractall(self._tmp_dir)
        if ext == 'whl':
            dir_path = self._tmp_dir
        else:
            dir_path = glob.glob('{}/**'.format(self._tmp_dir))[0]
        return dir_path

    @staticmethod
    def _rewrite_config_file(package_dir, package_name):
        if package_name == 'cloudshell-core':
            config_path = os.path.join(
                package_dir, 'cloudshell/core/logger/qs_config.ini'
            )
        elif package_name == 'cloudshell-logging':
            config_path = os.path.join(
                package_dir, 'cloudshell/logging/qs_config.ini'
            )
        else:
            raise ValueError('Unsupported package {}'.format(package_name))

        with open(config_path) as f:
            config_str = f.read()

        config_str = config_str.replace("'INFO'", "'DEBUG'")
        config_str = config_str.replace('"INFO"', '"DEBUG"')

        with open(config_path, 'w') as f:
            f.write(config_str)

    def _archive_folder_to_zip(self, dir_path, zip_path):
        with zipfile.ZipFile(zip_path, 'w') as zip_file:
            for cur_dir, sub_dirs, files in os.walk(dir_path):
                for file_name in files:
                    file_path = os.path.join(cur_dir, file_name)
                    if zip_path == file_path:
                        continue

                    file_arch_path = os.path.relpath(file_path, self._tmp_dir)
                    zip_file.write(file_path, file_arch_path)

    def _save_new_archive(self, archive_name, archive_ext, package_path):
        archive_path = os.path.join(self._tmp_dir, archive_name)
        if archive_ext in ('zip', 'whl'):
            self._archive_folder_to_zip(package_path, archive_path)
        elif archive_ext == 'tar.gz':
            with tarfile.open(archive_path, 'w:gz') as tar_file:
                tar_file.add(package_path, os.path.basename(package_path))
        else:
            raise ValueError('Unsupported archive type {}'.format(archive_ext))
        return archive_path

    def _remove_tmp_files(self):
        if self._tmp_dir is not None:
            shutil.rmtree(self._tmp_dir)
        if self._archive_obj is not None:
            self._archive_obj.close()

    def __enter__(self):
        """:rtype: file"""
        try:
            match = self.FILE_PATTERN.match(self._zip_ext_file.name)
            if not match:
                return self._zip_ext_file
    
            ext = match.group(5)
            package_name = match.group(1).replace('_', '-')
            buffer_ = BytesIO(self._zip_ext_file.read())
            extracted_dir = self._extract_archive(buffer_, ext)
            self._rewrite_config_file(extracted_dir, package_name)
            archive_path = self._save_new_archive(
                self._zip_ext_file.name, ext, extracted_dir
            )
            self._archive_obj = open(archive_path, 'rb')
        except Exception as e:
            self._remove_tmp_files()
            raise e

        return self._archive_obj

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._remove_tmp_files()
        return False
