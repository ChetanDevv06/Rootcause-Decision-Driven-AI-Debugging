"""Application that binds to a TCP port already held by another socket.

The program binds a listening socket to an ephemeral port, then attempts to
bind a second socket to the same port without SO_REUSEADDR. This deterministically
produces an "address already in use" OSError.
"""

import socket


def main() -> None:
    """Main entry point - fails when the port is already in use."""
    # Bind a listening socket to an ephemeral port to hold it.
    first = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    first.bind(("127.0.0.1", 0))
    first.listen(1)
    port = first.getsockname()[1]

    # Try to bind a second socket to the same port while the first still holds it.
    second = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        second.bind(("127.0.0.1", port))
    except OSError as exc:
        first.close()
        second.close()
        raise RuntimeError(
            f"Port already in use: cannot bind to 127.0.0.1:{port} "
            "because the address is already in use by another listener."
        ) from exc

    first.close()
    second.close()
    print(f"Bound to port {port}")


if __name__ == "__main__":
    main()
