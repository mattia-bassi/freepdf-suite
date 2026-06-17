"""FreePDF Suite plugin system.

NOTE: ``module-manager`` is a hyphenated source directory, NOT an importable
package (contract §2.1). Load these files via ``sys.path`` insertion of the repo
root + ``importlib``, e.g.::

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "freepdf_manager", "module-manager/manager.py")

Do not write ``from module-manager import ...`` — it is a SyntaxError.
"""
