"""Test that reproduces the port conflict failure."""

import socket


def test_port_conflict_reproduced():
    """Verify binding twice to the same held port raises OSError."""
    first = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    first.bind(("127.0.0.1", 0))
    first.listen(1)
    port = first.getsockname()[1]

    second = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        try:
            second.bind(("127.0.0.1", port))
            raise AssertionError("Expected OSError but bind succeeded")
        except OSError as exc:
            assert "address" in str(exc).lower() or "in use" in str(exc).lower()
    finally:
        first.close()
        second.close()


def test_app_raises_port_conflict():
    """Verify running the application raises RuntimeError about the port conflict."""
    import app  # noqa: F401

    try:
        app.main()
        raise AssertionError("Expected RuntimeError but main() succeeded")
    except RuntimeError as exc:
        assert "Port already in use" in str(exc)


if __name__ == "__main__":
    print("Running fixture reproduction tests...")

    try:
        test_port_conflict_reproduced()
        print("PASS: test_port_conflict_reproduced")
    except AssertionError as e:
        print(f"FAIL: test_port_conflict_reproduced - {e}")
        raise SystemExit(1)

    try:
        test_app_raises_port_conflict()
        print("PASS: test_app_raises_port_conflict")
    except AssertionError as e:
        print(f"FAIL: test_app_raises_port_conflict - {e}")
        raise SystemExit(1)

    print("\nAll reproduction tests passed!")
    print("Expected failure: RuntimeError: Port already in use")
