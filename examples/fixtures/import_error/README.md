# Incorrect Python Import Fixture

This fixture demonstrates a `ModuleNotFoundError` caused by an incorrect Python
import: the application imports `nonexistent_local_module`, which does not
exist on the import path.

## Expected Failure

When `app.py` is imported, Python raises `ModuleNotFoundError: No module named
'nonexistent_local_module'`.

## Files

| File | Purpose |
|------|---------|
| `app.py` | Imports a nonexistent local module at module level |
| `test_fixture.py` | Reproduces and verifies the failure |

## Command to Reproduce

```bash
cd examples/fixtures/import_error
python test_fixture.py
```

## Expected Error

```
ModuleNotFoundError: No module named 'nonexistent_local_module'
```

## Intended Diagnostic Evidence

When investigating this failure, Rootcause should discover:

1. **Source code** (`app.py`) imports `nonexistent_local_module` at module
   level (line 3).
2. **Dependency check** confirms `nonexistent_local_module` is not importable
   in the current environment (status: `missing`).

The root cause is an incorrect import statement referencing a module that does
not exist. A correct diagnosis should identify the failing import and the
missing module, without claiming the module exists under a different name
unless evidence supports it.

## Isolation

This fixture is independent of the Rootcause source directory and does not
require network access, a database, or external services.
