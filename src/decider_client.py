import json
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from typing import Final


DECIDER_URL: Final[str] = "http://127.0.0.1:8099/v1/systemone"
DECIDER_TIMEOUT: Final[int] = 30
MAX_EVIDENCE_CHARS: Final[int] = 50000


class DeciderError(Exception):
    """Base exception for Decider-related errors."""
    pass


class DeciderConnectionError(DeciderError):
    """Raised when Decider server is unreachable."""
    pass


class DeciderTimeoutError(DeciderError):
    """Raised when Decider request times out."""
    pass


class DeciderHTTPError(DeciderError):
    """Raised when Decider returns an HTTP error."""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"Decider HTTP {status_code}: {message}")


class DeciderInvalidResponseError(DeciderError):
    """Raised when Decider response is malformed or invalid."""
    pass


class DeciderValidationError(DeciderError):
    """Raised when Decider response fails validation."""
    pass


def _validate_decider_response(
    result: dict,
    available_actions: dict[str, str],
) -> dict:
    """Validate Decider response structure and selected action."""
    if not isinstance(result, dict):
        raise DeciderValidationError("Decider response is not a JSON object")

    if "answers" not in result:
        raise DeciderValidationError("Decider response missing 'answers' field")

    answers = result["answers"]
    if not isinstance(answers, dict) or "next_action" not in answers:
        raise DeciderValidationError("Decider response missing 'answers.next_action'")

    answer = answers["next_action"]
    if not isinstance(answer, dict):
        raise DeciderValidationError("Decider 'next_action' is not an object")

    if "choice" not in answer:
        raise DeciderValidationError("Decider response missing 'choice' field")

    selected = answer["choice"]
    if not isinstance(selected, str):
        raise DeciderValidationError("Decider 'choice' is not a string")

    # Never execute an action that was not explicitly offered.
    if selected not in available_actions:
        raise DeciderValidationError(
            f"Decider returned an invalid action: {selected}. "
            f"Available: {list(available_actions.keys())}"
        )

    return {
        "action": selected,
        "probabilities": answer.get("probabilities", {}),
        "confidence": answer.get("confidence"),
        "model": result.get("model"),
    }


def choose_next_action(
    error: str,
    evidence: list[str],
    available_actions: dict[str, str],
) -> dict:
    """Ask Decider to choose one of the available diagnostic actions.

    Args:
        error: The reported error message.
        evidence: List of evidence strings from previous steps.
        available_actions: Dictionary mapping action names to descriptions.

    Returns:
        Dictionary with selected action and metadata.

    Raises:
        DeciderConnectionError: If Decider server is unreachable.
        DeciderTimeoutError: If request times out.
        DeciderHTTPError: If Decider returns HTTP error.
        DeciderInvalidResponseError: If response is malformed JSON.
        DeciderValidationError: If response fails validation.
    """
    if not available_actions:
        raise DeciderValidationError("No available actions provided")

    # Bound evidence to prevent oversized requests
    bounded_evidence = []
    total_chars = 0
    for e in evidence:
        if total_chars + len(e) > MAX_EVIDENCE_CHARS:
            break
        bounded_evidence.append(e)
        total_chars += len(e)

    payload = {
        "state": {
            "error": error,
            "evidence": bounded_evidence,
            "available_actions": list(available_actions),
        },
        "questions": {
            "next_action": {
                "type": "choice",
                "instructions": (
                    "Choose the single most useful next diagnostic action. "
                    "Base your choice on the supplied evidence. "
                    "Choose only an option defined in criteria."
                ),
                "criteria": available_actions,
            }
        },
    }

    request = Request(
        DECIDER_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=DECIDER_TIMEOUT) as response:
            if response.status >= 400:
                body = response.read().decode("utf-8", errors="replace")
                raise DeciderHTTPError(response.status, body[:500])
            response_data = response.read().decode("utf-8")

    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise DeciderHTTPError(exc.code, body[:500])
    except URLError as exc:
        if isinstance(exc.reason, TimeoutError):
            raise DeciderTimeoutError(f"Decider request timed out after {DECIDER_TIMEOUT}s")
        raise DeciderConnectionError(f"Failed to connect to Decider: {exc}")
    except TimeoutError:
        raise DeciderTimeoutError(f"Decider request timed out after {DECIDER_TIMEOUT}s")

    try:
        result = json.loads(response_data)
    except json.JSONDecodeError as exc:
        raise DeciderInvalidResponseError(f"Decider returned invalid JSON: {exc}")

    return _validate_decider_response(result, available_actions)