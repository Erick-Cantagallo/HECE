# HECE/src/hece/__init__.py
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("hece")
except PackageNotFoundError:  # running from a source checkout without `pip install -e .`
    __version__ = "unknown"
