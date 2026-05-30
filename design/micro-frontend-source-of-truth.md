# Design: Micro-Frontend Standalone Source of Truth

## Overview
Previously, a compilation utility script `AIP/src/shared/create_sub_uis.py` was used to dynamically generate or overwrite static Micro-Frontend UIs for the various sub-applications. To ensure that modifications to individual product UIs are preserved as independent, standalone sources of truth without risking automatic regeneration or compilation overrides, `create_sub_uis.py` has been completely decommissioned and removed from the codebase.

## Architectural Changes

### Decommissioning of create_sub_uis.py
- **File Removal**: `AIP/src/shared/create_sub_uis.py` has been deleted from the repository.
- **Micro-Frontend Decentralization**: Individual sub-applications under their respective folders (e.g., `AIP/src/kms/ui`, `AIP/src/reporting/prism/ui`, etc.) now possess their own standalone, permanent HTML, CSS, and JS files as the absolute sources of truth.
- **Central Gateway Integration**: The gateway routing layer in `AIP/src/main.py` continues to serve these independent folders statically.

### Verification and Test Changes
- **Reference Cleanup**: The test suite in [tests/test_ui_auth_paths.py](file:///Users/chethan/GitHub/AIP-Project/tests/test_ui_auth_paths.py) has been updated to remove references to the deleted generator script.
- **Automated Validation**: Tests continue to recursively locate and validate individual `index.html` micro-frontends to verify same-origin API routes and authentication token resolution behavior.
