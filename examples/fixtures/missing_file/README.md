# Incorrect File Path Fixture

This fixture demonstrates a `FileNotFoundError` caused by an incorrect relative
file path: the application attempts to read `nonexistent_data.txt`, which does
not exist in the project directory.

## Expected Failure

When `app.py` runs, `open("nonexistent_data.txt")` raises
`FileNotFoundError: [Errno 2] No such file or directory: 'nonexistent_data.txt'`.

## Files

| File | Purpose |
|------|---------|
| `app.py` | Attempts to open `nonexistent_data.txt` with an incorrect path |
| `test_fixture.py` | Reproduces and verifies the failure |

## Command to Reproduce

```bash
cd examples/fixtures/missing_file
python test_fixture.py
```

## Expected Error

```
FileNotFoundError: [Errno 2] No such file or directory: 'nonexistent_data.txt'
```

## Intended Diagnostic Evidence

When investigating this failure, Rootcause should discover:

1. **Source code** (`app.py`) opens `nonexistent_data.txt` with a relative
   path (no directory resolution or existence check).
2. The error message identifies the exact path that could not be found.

The root cause is an incorrect file path. A correct diagnosis should suggest
a corrected path or a robust path-resolution approach (e.g., resolving the
path relative to the script location or checking existence before opening),
without modifying any project files.

## Isolation

This fixture is independent of the Rootcause source directory and does not
require network access, a database, or external services.
