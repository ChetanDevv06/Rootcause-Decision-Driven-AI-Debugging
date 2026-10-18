# Syntax Error Fixture

This fixture demonstrates a `SyntaxError` caused by a deliberate syntax error
in `broken.py` (an unterminated function definition).

## Expected Failure

When Python parses `broken.py`, it raises `SyntaxError: invalid syntax` (or
similar) pointing at the malformed `def broken_function(` line.

## Files

| File | Purpose |
|------|---------|
| `broken.py` | Contains a deliberate syntax error (unterminated `def`) |
| `working.py` | A correctly defined function for contrast |
| `test_fixture.py` | Reproduces and verifies the failure |

## Command to Reproduce

```bash
cd examples/fixtures/syntax_error
python test_fixture.py
# or
python -m py_compile broken.py
```

## Expected Error

```
SyntaxError: invalid syntax
```

## Intended Diagnostic Evidence

When investigating this failure, Rootcause should discover:

1. **Source code** (`broken.py`) contains the malformed `def broken_function(`
   definition that Python cannot parse.
2. The error message identifies the file and the syntax error reported by the
   parser.

The root cause is a syntax error in `broken.py`. A correct diagnosis should
identify the relevant file and provide the smallest correction supported by the
parser output, without executing the broken file.

## Isolation

This fixture is independent of the Rootcause source directory and does not
require network access, a database, or external services.
