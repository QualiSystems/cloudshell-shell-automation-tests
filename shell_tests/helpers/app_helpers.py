from shell_tests.configs import MainConfig
from shell_tests.helpers.handler_storage import HandlerStorage
from shell_tests.helpers.package_api.models import App, Blueprint, DeploymentPath
from shell_tests.helpers.package_api.package_api import PackageApi


def _get_app_models(conf: MainConfig, handler_storage: HandlerStorage) -> list[App]:
    apps = []
    for app_conf in conf.apps_conf:
        cp = handler_storage.resource_handlers_dict[app_conf.cp_resource_name]
        dp = DeploymentPath(cp.name, cp.model, app_conf.deployment, app_conf.attributes)
        app = App(app_conf.name, [dp])
        apps.append(app)
    return apps


def create_apps(conf: MainConfig, handler_storage: HandlerStorage):
    apps = _get_app_models(conf, handler_storage)
    with PackageApi.create_package() as package:
        for app in apps:
            package.add_app(app)
        handler_storage.cs_handler.import_package(package.zip_path)


def create_blueprints(conf: MainConfig, handler_storage: HandlerStorage):
    apps_dict = {app.name: app for app in _get_app_models(conf, handler_storage)}
    with PackageApi.create_package() as package:
        for blueprint_conf in conf.blueprints_conf:
            bp_apps = list(map(apps_dict.__getitem__, blueprint_conf.app_names))
            bp = Blueprint(blueprint_conf.name, bp_apps)
            package.add_blueprint(bp)
        handler_storage.cs_handler.import_package(package.zip_path)
