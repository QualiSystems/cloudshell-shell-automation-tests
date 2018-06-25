import os
import tempfile
import urllib2
import urlparse
import zipfile
from contextlib import closing

import yaml


DOWNLOAD_FOLDER = 'shell_tests'


def get_resource_family_and_model(shell_path, logger):
    """Get resource family and model from shell-definition.yaml

    :param str shell_path: path to Shell zip
    :param logging.Logger logger:
    :return: family and model
    :rtype: tuple[str, str]"""

    with zipfile.ZipFile(shell_path) as zip_file:
        data = yaml.load(zip_file.read('shell-definition.yaml'))

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
