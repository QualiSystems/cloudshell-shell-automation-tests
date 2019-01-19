import io
import os
import platform
import re
import subprocess
import tempfile
import urllib2
import urlparse
import zipfile
from contextlib import closing
from xml.etree import ElementTree

import yaml


DOWNLOAD_FOLDER = 'shell_tests'


def get_resource_family_and_model(shell_path, logger):
    """Get resource family and model from shell-definition.yaml

    :param str shell_path: path to Shell zip
    :param logging.Logger logger:
    :return: family and model
    :rtype: tuple[str, str]"""

    with zipfile.ZipFile(shell_path) as zip_file:
        data = yaml.safe_load(zip_file.read('shell-definition.yaml'))

    model = data['node_types'].keys()[0].rsplit('.', 1)[-1]
    family = data['node_types'].values()[0]['derived_from'].rsplit('.', 1)[-1]
    family = 'CS_{}'.format(family)  # todo get it from standard
    logger.debug('Family: {}, model: {} for the Shell {}'.format(
        family, model, shell_path))
    return family, model


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
    driver_metadata = get_driver_metadata(shell_path)

    doc = ElementTree.fromstring(driver_metadata)
    commands = doc.findall('Layout/Category/Command')
    commands.extend(doc.findall('Layout/Command'))

    return [command.get('Name') for command in commands]
