import concurrent.futures as ft
import re
from typing import TYPE_CHECKING

from shell_tests.configs import SandboxConfig
from shell_tests.errors import BaseAutomationException
from shell_tests.handlers.sandbox_handler import SandboxHandler
from shell_tests.helpers.dependencies_helpers import patch_dependencies
from shell_tests.helpers.logger import logger
from shell_tests.helpers.package_api import BP_SCRIPT_PATH

if TYPE_CHECKING:
    from shell_tests.handlers.resource_handler import ResourceHandler
    from shell_tests.helpers.handler_storage import HandlerStorage


def generate_new_resource_name(name: str) -> str:
    """Create new name with index."""
    try:
        match = re.search(r"^(?P<name>.+)-(?P<v>\d+)$", name)
        version = int(match.group("v"))
        name = match.group("name")
    except (AttributeError, KeyError):
        version = 0

    return f"{name}-{version + 1}"


def _set_debug_log_level_for_resource(
    resource: "ResourceHandler",
    sandbox: SandboxHandler,
    handler_storage: "HandlerStorage",
):
    sandbox.add_resource_to_reservation(resource)

    # run some command for creating venv
    resource.health_check()

    # find venv

    prefix_venv_name = f"{resource.model.replace(' ', '_')}_"
    venv_names = handler_storage.cs_smb_handler.get_venv_names()
    suitable_venv_names = [
        venv_name for venv_name in venv_names if venv_name.startswith(prefix_venv_name)
    ]
    if not suitable_venv_names:
        raise BaseAutomationException(
            f"venv for the {resource.name} is not found. venv names are {venv_names}"
        )
    venv_name = max(
        suitable_venv_names,
        key=lambda name: int(name.replace(prefix_venv_name, "").split("_")[0]),
    )

    # change qs_config.ini
    data = handler_storage.cs_smb_handler.get_qs_config(venv_name)
    data = data.replace(b"LOG_LEVEL='INFO'", b"LOG_LEVEL='DEBUG'")
    handler_storage.cs_smb_handler.put_qs_config(venv_name, data)


def _set_log_level_via_sandbox(handler_storage: "HandlerStorage"):
    logger.info(
        "Setting debug log level via creating virtualenv and changing qs_config.ini"
    )
    sandbox_conf = SandboxConfig(Name="tmp-sandbox", Resources=[])
    temp_sandbox = SandboxHandler.create(sandbox_conf, handler_storage.cs_handler)

    try:
        with ft.ThreadPoolExecutor(
            5, thread_name_prefix="[set-debug-level]"
        ) as executor:
            futures = {
                executor.submit(
                    _set_debug_log_level_for_resource, rh, temp_sandbox, handler_storage
                )
                for rh in handler_storage.resource_handlers
            }
            ft.wait(futures)
            for future in futures:
                future.result()
    finally:
        temp_sandbox.finish(wait=False)


def set_debug_log_level(handler_storage: "HandlerStorage"):
    if any(conf.dependencies_path for conf in handler_storage.conf.shells_conf):
        for conf in handler_storage.conf.shells_conf:
            patch_dependencies(conf.dependencies_path)
    else:
        _set_log_level_via_sandbox(handler_storage)


def set_debug_level_via_blueprint(cs):
    cs.import_package(BP_SCRIPT_PATH)
    rid = cs.create_topology_reservation("scripts", topology_name="scripts")
    cs.execute_reservation_command(rid, "set_debug_logs")
