class BaseAutomationException(Exception):
    """Base Exception."""


class ResourceIsNotAliveError(BaseAutomationException):
    """Resource that needed for tests is not alive."""


class CSIsNotAliveError(ResourceIsNotAliveError):
    """Can't connect to CS."""


class DeploymentResourceNotFoundError(BaseAutomationException):
    """Could not find a deployment resource."""


class CreationReservationError(BaseAutomationException):
    """Error with creating a reservation."""
