"""Phase 0 smoke test: does the package actually install and import?

Real tests (geometry validity, NDVI range checks, raster alignment,
threshold logic, hectare math) arrive in later phases alongside the
code they test.
"""

import forest_change


def test_package_imports_and_has_version():
    assert forest_change.__version__ == "0.1.0"
