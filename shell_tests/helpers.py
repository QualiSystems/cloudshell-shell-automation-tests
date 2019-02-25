import io
import os
import platform
import re
import subprocess
import sys
import tempfile
import threading
import time
import urllib2
import urlparse
import zipfile
from contextlib import closing
from functools import wraps
from xml.etree import ElementTree

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
