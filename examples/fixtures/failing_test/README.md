# Failing Unit Test Fixture

This fixture demonstrates a deterministic failing unit test caused by a
genuine implementation defect: `calculator.add` subtracts instead of adding.

## Expected Failure

Running `pytest` on `test_calculator.py` produces a failure:
`assert add(2, 3) == 5` fails because `add(2, 3)` returns `-1`.

## Files

| File | Purpose |
|------|---------|
| `calculator.py` | Contains the defective `add` function (returns `a - b`) |
| `test_calculator.py` | Tests that `add(2, 3) == 5` (fails) |
| `test_fixture.py` | Reproduces and verifies the failure |

## Command to Reproduce

```bash
cd examples/fixtures/failing_test
python test_fixture.py
# or
python -m pytest test_calculator.py -v
```

## Expected Error

```
def test_add():
    assert add(2, 3) == 5
E   AssertionError: Expected 5, got -1
```

## Intended Diagnostic Evidence

When investigating this failure, Rootcause should discover:

1. **Test output** (`run_tests`) shows `test_add` failed: expected `5`, got
   `-1`.
2. **Source code** (`calculator.py`) shows `add` returns `a - b` instead of
   `a + b` (the implementation defect).

The root cause is an incorrect implementation in `calculator.add`. A correct
diagnosis should identify `a - b` as the bug and suggest changing it to
`a + b`. This scenario is distinct from the missing-dependency fixture.

## Isolation

This fixture is independent of the Rootcause source directory and does not
require network access, a database, or external services.
