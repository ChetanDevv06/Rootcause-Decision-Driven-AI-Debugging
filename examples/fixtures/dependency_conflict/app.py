"""Application with an intentional dependency version conflict.

package-a requires shared-lib>=2.0 while package-b requires shared-lib<1.0.
The version guard below raises a RuntimeError when the shared library version
cannot be resolved to satisfy both constraints.
"""

import importlib.metadata


def main() -> None:
    """Raise a dependency conflict error simulating an unresolvable constraint."""
    try:
        version = importlib.metadata.version("shared-lib")
    except importlib.metadata.PackageNotFoundError:
        version = None

    if version is None:
        raise RuntimeError(
            "Dependency conflict: shared-lib is required but not installed. "
            "package-a requires shared-lib>=2.0 while package-b requires "
            "shared-lib<1.0, so no single version can satisfy both."
        )

    raise RuntimeError(
        f"Dependency conflict: shared-lib {version} cannot satisfy both "
        "package-a (requires >=2.0) and package-b (requires <1.0)."
    )


if __name__ == "__main__":
    main()
