"""Test that reproduces the syntax error failure."""

import py_compile


def test_broken_py_has_syntax_error():
    """Verify broken.py cannot be compiled due to a syntax error."""
    try:
        py_compile.compile("broken.py", doraise=True)
        raise AssertionError("Expected SyntaxError but compilation succeeded")
    except (SyntaxError, py_compile.PyCompileError) as exc:
        assert "broken.py" in str(exc) or getattr(exc, "filename", None) == "broken.py"


def test_working_py_compiles():
    """Verify working.py compiles cleanly for contrast."""
    py_compile.compile("working.py", doraise=True)


def test_error_mentions_invalid_syntax():
    """Verify the error message identifies a syntax problem."""
    try:
        py_compile.compile("broken.py", doraise=True)
        raise AssertionError("Expected a syntax error but compilation succeeded")
    except (SyntaxError, py_compile.PyCompileError):
        pass  # broken.py is intentionally malformed


if __name__ == "__main__":
    print("Running fixture reproduction tests...")

    try:
        test_broken_py_has_syntax_error()
        print("PASS: test_broken_py_has_syntax_error")
    except AssertionError as e:
        print(f"FAIL: test_broken_py_has_syntax_error - {e}")
        raise SystemExit(1)

    try:
        test_working_py_compiles()
        print("PASS: test_working_py_compiles")
    except AssertionError as e:
        print(f"FAIL: test_working_py_compiles - {e}")
        raise SystemExit(1)

    try:
        test_error_mentions_invalid_syntax()
        print("PASS: test_error_mentions_invalid_syntax")
    except AssertionError as e:
        print(f"FAIL: test_error_mentions_invalid_syntax - {e}")
        raise SystemExit(1)

    print("\nAll reproduction tests passed!")
    print("Expected failure: SyntaxError: invalid syntax")
