from setuptools import setup, find_packages


def get_file_content(file_path):
    with open(file_path) as fp:
        return fp.read()


setup(
    name='shell_tests',
    url='http://www.qualisystem.com/',
    author_email='info@qualisystems.com',
    packages=find_packages(),
    install_requires=get_file_content('requirements.txt'),
    version=get_file_content('version.txt'),
    description='QualiSystems automation tests for Shells',
    include_package_data=True,
    entry_points={'console_scripts': ['shell_tests = shell_tests.cli:cli']},
)
