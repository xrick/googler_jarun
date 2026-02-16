"""Import bridge to googler internals.

Uses importlib to load the googler executable (no .py extension)
as a Python module without modifying the original file.
"""

import importlib.machinery
import importlib.util
import pathlib
import sys

_MODULE_NAME = "_googler_internals"


def _import_googler():
    """Import the googler executable as a Python module.

    The googler file has no .py extension, so we must explicitly
    use SourceFileLoader to tell Python it is Python source code.

    Returns the module object with all googler internals accessible.

    Raises
    ------
    FileNotFoundError
        If the googler executable is not found.
    ImportError
        If the module fails to load.
    """
    # Already loaded
    if _MODULE_NAME in sys.modules:
        return sys.modules[_MODULE_NAME]

    googler_path = pathlib.Path(__file__).resolve().parent.parent / "googler"
    if not googler_path.exists():
        raise FileNotFoundError(
            f"googler executable not found at {googler_path}. "
            "Ensure googler_api is installed alongside the googler file."
        )

    # Explicitly use SourceFileLoader since the file has no .py extension
    loader = importlib.machinery.SourceFileLoader(_MODULE_NAME, str(googler_path))
    spec = importlib.util.spec_from_file_location(
        _MODULE_NAME,
        googler_path,
        loader=loader,
    )
    if spec is None:
        raise ImportError(f"Cannot create module spec from {googler_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[_MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module


_googler = _import_googler()

# Re-export the classes and functions we need
GoogleUrl = _googler.GoogleUrl
GoogleConnection = _googler.GoogleConnection
GoogleConnectionError = _googler.GoogleConnectionError
GoogleParser = _googler.GoogleParser
Result = _googler.Result
Sitelink = _googler.Sitelink
