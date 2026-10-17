# Missing Dependency Fixture

This fixture demonstrates a `ModuleNotFoundError: No module named 'psycopg'` failure caused by a missing Python dependency.

## Expected Failure

When the application attempts to import `psycopg` (a PostgreSQL database adapter), Python raises a `ModuleNotFoundError` because the package is not installed in the current environment.

## Files

| File | Purpose |
|------|---------|
| `requirements.txt` | Declares the required dependency: `psycopg[binary]>=3.2` |
| `app.py` | Sample application that imports and uses `psycopg` |
| `test_fixture.py` | Reproduces and verifies the failure |

## Command to Reproduce

### Option 1: Run the test directly (recommended)

```bash
cd examples/fixtures/missing_dependency
python test_fixture.py
```

**Expected output:**
```
Running fixture reproduction tests...
PASS: test_missing_psycopg_raises_import_error
PASS: test_app_module_import_fails_without_psycopg
PASS: test_error_message_contains_module_name

All reproduction tests passed!
Expected failure: ModuleNotFoundError: No module named 'psycopg'
```

### Option 2: Import the app module directly

```bash
cd examples/fixtures/missing_dependency
python -c "import app"
```

**Expected error:**
```
Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File "E:\...\examples\fixtures\missing_dependency\app.py", line 3, in <module>
    import psycopg
ModuleNotFoundError: No module named 'psycopg'
```

### Option 3: Run with pytest (if available)

```bash
cd examples/fixtures/missing_dependency
python -m pytest test_fixture.py -v
```

## Expected Error

```
ModuleNotFoundError: No module named 'psycopg'
```

## Intended Diagnostic Evidence

When investigating this failure, Rootcause should discover:

1. **Dependency manifest** (`requirements.txt`) declares `psycopg[binary]>=3.2` as a required dependency.
2. **Source code** (`app.py`) imports `psycopg` at module level (line 3).
3. **Test output** confirms the import fails with `ModuleNotFoundError`.
4. **No virtual environment** has `psycopg` installed in the current Python environment.

The root cause is that the declared dependency is not installed. The fix is to install the dependencies:

```bash
pip install -r requirements.txt
```

## How to Reset the Fixture

The fixture is designed to work **without** `psycopg` installed. To reset after accidentally installing it:

```bash
pip uninstall psycopg psycopg-binary -y
```

Then verify the failure reproduces:

```bash
python test_fixture.py
```

## Isolation

This fixture is completely independent of the Rootcause source directory:
- It has its own `requirements.txt`
- It does not share dependencies with Rootcause's `.venv314`
- Running tests here will not affect Rootcause's environment
- Rootcause can target this directory via `--project-path examples/fixtures/missing_dependency`

## Notes

- The fixture does not require a real PostgreSQL database, network connection, or external service.
- The failure is deterministic and reproducible in any clean Python environment.
- The test uses `importlib.util.find_spec()` to verify the module is absent without triggering side effects.