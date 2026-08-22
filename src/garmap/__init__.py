"""Build routable, cycling-tuned Garmin .img maps covering a GPX route."""

__version__ = "0.1.0"


class GarmapError(Exception):
    """Base class for errors we expect and report nicely to the user."""
