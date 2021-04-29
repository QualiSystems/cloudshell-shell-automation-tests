import os
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import Optional
from zipfile import ZipFile

from shell_tests.helpers.logger import logger
from shell_tests.helpers.package_api import PYTHON_DRIVER_PATH
from shell_tests.helpers.package_api.models import App, Blueprint, MetaData


class PackageApi:
    def __init__(self, zip_path: Path):
        self.zip_path = zip_path
        self._driver_added = False

    def finish(self):
        with suppress(FileNotFoundError):
            os.remove(self.zip_path)

    def add_metadata(self, metadata: MetaData):
        with ZipFile(self.zip_path, "a") as zf:
            zf.writestr("metadata.xml", metadata.get_xml())

    def add_app(self, app: App):
        logger.info(f"Adding a new app {app.name} to the package")
        with ZipFile(self.zip_path, "a") as zf:
            zf.writestr(f"App Templates/{app.name}.xml", app.get_xml())

    def add_blueprint(self, blueprint: Blueprint):
        self.add_python_driver()
        logger.info(f"Adding a new blueprint {blueprint.name} to the package")
        with ZipFile(self.zip_path, "a") as zf:
            zf.writestr(f"Topologies/{blueprint.name}.xml", blueprint.get_xml())

    def add_python_driver(self):
        if not self._driver_added:
            logger.info("Add Python driver to the package")
            with ZipFile(self.zip_path, "a") as zf:
                zf.write(
                    PYTHON_DRIVER_PATH, f"Topology Drivers/{PYTHON_DRIVER_PATH.name}"
                )
            self._driver_added = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        logger.info("Deleting the package")
        self.finish()
        return False

    @classmethod
    def create_package(cls, cs_version: Optional[str] = None) -> "PackageApi":
        logger.info("Creating a new package")
        path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False) as fo:
                path = fo.name
            with ZipFile(path, mode="w"):
                # creates empty zip file
                pass
        except Exception as e:
            if path:
                os.unlink(path)
            raise e

        package = cls(Path(path))
        try:
            package.add_metadata(MetaData(cs_version))
        except Exception as e:
            package.finish()
            raise e
        return package
