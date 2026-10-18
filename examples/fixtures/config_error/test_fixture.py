"""Test that reproduces the configuration file error failure."""

import json


def test_config_json_is_malformed():
    """Verify config.json cannot be parsed as JSON."""
    with open("config.json", "r", encoding="utf-8") as fh:
        try:
            json.load(fh)
            raise AssertionError("Expected JSONDecodeError but parsing succeeded")
        except json.JSONDecodeError:
            pass  # config.json is intentionally malformed


def test_app_raises_json_decode_error():
    """Verify running the application raises JSONDecodeError loading config."""
    import app  # noqa: F401

    try:
        app.main()
        raise AssertionError("Expected JSONDecodeError but main() succeeded")
    except json.JSONDecodeError as exc:
        assert exc.doc is not None or "config.json" in str(exc)


if __name__ == "__main__":
    print("Running fixture reproduction tests...")

    try:
        test_config_json_is_malformed()
        print("PASS: test_config_json_is_malformed")
    except AssertionError as e:
        print(f"FAIL: test_config_json_is_malformed - {e}")
        raise SystemExit(1)

    try:
        test_app_raises_json_decode_error()
        print("PASS: test_app_raises_json_decode_error")
    except AssertionError as e:
        print(f"FAIL: test_app_raises_json_decode_error - {e}")
        raise SystemExit(1)

    print("\nAll reproduction tests passed!")
    print("Expected failure: json.JSONDecodeError parsing config.json")
