# Port Already in Use Fixture

This fixture demonstrates an `OSError` / `RuntimeError` caused by attempting to
bind a TCP port that is already occupied by another listener.

## Expected Failure

When `app.py` runs, it holds an ephemeral port with one socket then attempts to
bind a second socket to the same port, raising an `OSError: [Errno 98] Address
already in use` (Windows: `[WinError 10048]`), which is re-raised as a
`RuntimeError: Port already in use`.

## Files

| File | Purpose |
|------|---------|
| `app.py` | Holds a port then tries to bind a second socket to it |
| `test_fixture.py` | Reproduces and verifies the failure |

## Command to Reproduce

```bash
cd examples/fixtures/port_conflict
python test_fixture.py
```

## Expected Error

```
RuntimeError: Port already in use: cannot bind to 127.0.0.1:<port> ...
```

## Intended Diagnostic Evidence

When investigating this failure, Rootcause should discover:

1. **Source code** (`app.py`) calls `socket.bind(("127.0.0.1", port))` on a
   port already held by another socket in the same process.
2. The error is an `OSError` / `RuntimeError` about the address being in use,
   distinct from a network connectivity failure (the local interface is fine;
   the specific port is occupied).

The root cause is a port conflict, not a network outage. A correct diagnosis
should explain that the address cannot be bound because another listener
already holds it, and suggest checking the existing listener or choosing
another available port. It should not terminate arbitrary user processes.

## Isolation

This fixture is independent of the Rootcause source directory and does not
require network access beyond localhost, a database, or external services.
