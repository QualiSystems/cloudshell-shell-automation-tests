class BaseAutomationException(Exception):
    """Base Exception"""


class ResourceIsNotAliveError(BaseAutomationException):
    """Resource that needed for tests is not alive"""
