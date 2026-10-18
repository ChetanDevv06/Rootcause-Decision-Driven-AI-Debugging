"""Test that reproduces the database connection failure."""

import socket


def test_connection_refused():
    """Verify connecting to 127.0.0.1:54321 raises ConnectionRefusedError."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        try:
            sock.connect(("127.0.0.1", 54321))
            raise AssertionError("Expected ConnectionRefusedError but connect succeeded")
        except ConnectionRefusedError:
            pass
        except OSError as exc:
            assert "refused" in str(exc).lower() or "connect" in str(exc).lower()
    finally:
        sock.close()


def test_app_raises_database_connection_failure():
    """Verify running the application raises RuntimeError about the connection."""
    import app  # noqa: F401

    try:
        app.main()
        raise AssertionError("Expected RuntimeError but main() succeeded")
    except RuntimeError as exc:
        message = str(exc)
        assert "Database connection failure" in message
        assert "127.0.0.1:54321" in message


if __name__ == "__main__":
    print("Running fixture reproduction tests...")

    try:
        test_connection_refused()
        print("PASS: test_connection_refused")
    except AssertionError as e:
        print(f"FAIL: test_connection_refused - {e}")
        raise SystemExit(1)

    try:
        test_app_raises_database_connection_failure()
        print("PASS: test_app_raises_database_connection_failure")
    except AssertionError as e:
        print(f"FAIL: test_app_raises_database_connection_failure - {e}")
        raise SystemExit(1)

    print("\nAll reproduction tests passed!")
    print("Expected failure: RuntimeError: Database connection failure")
