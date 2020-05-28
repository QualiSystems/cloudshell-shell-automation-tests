import re


def generate_new_resource_name(name: str) -> str:
    """Create new name with index."""
    try:
        match = re.search(r"^(?P<name>.+)-(?P<v>\d+)$", name)
        version = int(match.group("v"))
        name = match.group("name")
    except (AttributeError, KeyError):
        version = 0

    return f"{name}-{version + 1}"
