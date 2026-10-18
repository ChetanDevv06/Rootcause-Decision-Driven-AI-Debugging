# Database Connection Failure Fixture

This fixture demonstrates a `ConnectionRefusedError` / `RuntimeError` caused by
attempting a database connection to an unavailable local endpoint
(`127.0.0.1:54321`) where nothing is listening.

## Expected Failure

When `app.py` runs, `socket.connect(("127.0.0.1", 54321))` raises
`ConnectionRefusedError`, which is re-raised as a `RuntimeError: Database
connection failure: could not connect to 127.0.0.1:54321`.

## Files

| File | Purpose |
|------|---------|
| `app.py` | Attempts a TCP connection to an unavailable database port |
| `test_fixture.py` | Reproduces and verifies the failure |

## Command to Reproduce

```bash
cd examples/fixtures/database_connection
python test_fixture.py
```

## Expected Error

```
RuntimeError: Database connection failure: could not connect to
127.0.0.1:54321 (connection refused). ...
```

## Intended Diagnostic Evidence

When investigating this failure, Rootcause should discover:

1. **Source code** (`app.py`) attempts `socket.connect(("127.0.0.1", 54321))`.
2. The error is a connection refusal (`ConnectionRefusedError` / OSError), not
   an authentication failure or a missing driver.

The root cause is that the database endpoint is not accepting connections. A
correct diagnosis should distinguish connection refusal from authentication
errors or missing drivers, and explain what to verify (host, port, server
running). It should not label every database exception as an authentication
failure, and it should not require a real database, credentials, or external
infrastructure.

## Isolation

This fixture is independent of the Rootcause source directory and does not
require a real database, credentials, or external services.
