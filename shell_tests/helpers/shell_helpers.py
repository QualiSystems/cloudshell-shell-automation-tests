import zipfile
from pathlib import Path

import yaml

from shell_tests.helpers.logger import logger


def get_resource_model_from_shell_definition(shell_path: Path) -> str:
    """Get resource family and model from shell-definition.yaml."""
    with zipfile.ZipFile(shell_path) as zip_file:
        data = yaml.safe_load(zip_file.read("shell-definition.yaml"))

    node_type = next(iter(data["node_types"]))
    model = node_type.rsplit(".", 1)[-1]
    logger.debug("Model: {} for the Shell {}".format(model, shell_path))
    return model


def get_shell_name_from_shell_definition(shell_path: Path) -> str:
    with zipfile.ZipFile(shell_path) as zip_file:
        data = yaml.safe_load(zip_file.read("shell-definition.yaml"))

    return data["metadata"]["template_name"]
