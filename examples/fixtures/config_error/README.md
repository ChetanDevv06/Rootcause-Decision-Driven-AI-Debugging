# Configuration File Error Fixture

This fixture demonstrates a `json.JSONDecodeError` caused by a malformed
configuration file (`config.json` is truncated and missing its closing braces).

## Expected Failure

When `app.py` runs, `json.load(open("config.json"))` raises
`json.JSONDecodeError: Expecting value: ...` because `config.json` is invalid.

## Files

| File | Purpose |
|------|---------|
| `app.py` | Loads and parses `config.json` with `json.load` |
| `config.json` | Intentionally malformed JSON (missing closing braces) |
| `test_fixture.py` | Reproduces and verifies the failure |

## Command to Reproduce

```bash
cd examples/fixtures/config_error
python test_fixture.py
```

## Expected Error

```
json.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

## Intended Diagnostic Evidence

When investigating this failure, Rootcause should discover:

1. **Source code** (`app.py`) opens and parses `config.json` with
   `json.load(fh)`.
2. The error message identifies a JSON parsing failure at the start of the
   file.

Note: `config.json` is not a Python source file or dependency manifest, so
the diagnostic tools will not read its contents directly. The diagnosis relies
on `app.py` source plus the reported `json.JSONDecodeError`. A correct
diagnosis should identify the configuration parsing failure and point at
`config.json` as the file needing correction, without automatically rewriting
it.

## Isolation

This fixture is independent of the Rootcause source directory and does not
require network access, a database, or external services.
