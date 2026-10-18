"""Python module containing a deliberate syntax error.

The function definition below is missing its closing parenthesis and colon
structure, so Python reports a SyntaxError when the file is parsed.
"""

import os  # noqa: F401


def broken_function(   # <-- missing closing paren and body
    pass


def working_function() -> None:
    """A correctly defined function for contrast."""
    print("this one parses fine")
