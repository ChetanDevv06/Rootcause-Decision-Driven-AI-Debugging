# Dependency Conflict Fixture

This fixture demonstrates a `RuntimeError` caused by an unresolvable Python
dependency version conflict: `package-a` requires `shared-lib>=2.0` while
`package-b` requires `shared-lib<1.0`.

## Expected Failure

When `app.py` runs, it attempts to resolve the `shared-lib` version and raises
a `RuntimeError` describing the conflict because no single version can satisfy
both constraints.

## Files

| File | Purpose |
|------|---------|
| `app.py` | Version guard that raises the dependency conflict error |
| `requirements.txt` | Declares `package-a>=2.0` and `package-b>=1.0` (conflicting via `shared-lib`) |
| `test_fixture.py` | Reproduces and verifies the failure |

## Command to Reproduce

```bash
cd examples/fixtures/dependency_conflict
python test_fixture.py
```

## Expected Error

```
RuntimeError: Dependency conflict: shared-lib is required but not installed. ...
```

## Intended Diagnostic Evidence

When investigating this failure, Rootcause should discover:

1. **Dependency manifest** (`requirements.txt`) declares `package-a>=2.0`
   and `package-b>=1.0`.
2. **Source code** (`app.py`) contains a version guard that raises the
   dependency conflict error when `shared-lib` cannot be resolved.
3. The `shared-lib` module is not installed in the current environment.

The root cause is a declared dependency version conflict that cannot be
satisfied. A correct diagnosis should identify the conflicting version
constraints in `requirements.txt` and the raised `RuntimeError`, without
claiming a specific runtime package version was verified (the module may not
be installed).

## How to Reset the Fixture

No installation is required. Re-run `python test_fixture.py` to reproduce.

## Isolation

This fixture is independent of the Rootcause source directory and does not
require network access, a database, or external services.
