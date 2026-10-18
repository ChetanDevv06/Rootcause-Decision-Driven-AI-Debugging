# Missing Environment Variable Fixture

This fixture demonstrates a `RuntimeError` caused by a missing environment
variable: the application requires `DATABASE_URL` and fails clearly when it is
not set.

## Expected Failure

When `app.py` runs without `DATABASE_URL` in the environment, it raises
`RuntimeError: Missing environment variable: DATABASE_URL is not set.`

## Files

| File | Purpose |
|------|---------|
| `app.py` | Reads `DATABASE_URL` from the environment and raises when missing |
| `test_fixture.py` | Reproduces and verifies the failure |

## Command to Reproduce

```bash
cd examples/fixtures/missing_env
# Ensure DATABASE_URL is not set, then run:
python test_fixture.py
```

## Expected Error

```
RuntimeError: Missing environment variable: DATABASE_URL is not set. ...
```

## Intended Diagnostic Evidence

When investigating this failure, Rootcause should discover:

1. **Source code** (`app.py`) reads `os.environ.get("DATABASE_URL")` and
   raises a `RuntimeError` when the value is falsy.
2. The error message explicitly names the missing configuration key
   (`DATABASE_URL`).

The root cause is a missing required environment variable. A correct diagnosis
should identify `DATABASE_URL` as the missing key and explain how to configure
it, without printing or exposing any real environment secret or inventing a
production value.

## How to Reset the Fixture

No installation is required. Ensure `DATABASE_URL` is unset, then run
`python test_fixture.py`.

## Isolation

This fixture is independent of the Rootcause source directory and does not
require network access, a database, credentials, or external services.
