from subprocess import PIPE, Popen

import xmltodict

CONF_PATH = (
    r"C:\Program Files (x86)\QualiSystems\TestShell\ExecutionServer\customer.config"
)


def set_log_level(level="DEBUG"):
    value_str = f"LOG_LEVEL={level}"
    with open(CONF_PATH) as fo:
        str_data = fo.read()

    data = xmltodict.parse(str_data)
    settings = data["appSettings"]["add"]
    for setting in settings:
        if setting["@key"] == "DefaultPythonEnvrionmentVariables":
            setting["@value"] = value_str
            break
    else:
        settings.append(
            {"@key": "DefaultPythonEnvrionmentVariables", "@value": value_str}
        )

    with open(CONF_PATH, "w") as fo:
        fo.write(xmltodict.unparse(data, pretty=True, short_empty_elements=True))

    cmd = (
        'net stop "TestShell Execution Server" '
        '&& net start "TestShell Execution Server"'
    )
    Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)


if __name__ == "__main__":
    set_log_level("DEBUG")
