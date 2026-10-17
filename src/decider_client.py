
import json
from urllib.request import Request, urlopen


DECIDER_URL = "http://127.0.0.1:8099/v1/systemone"


def choose_next_action(
    error: str,
    evidence: list[str],
    available_actions: dict[str, str],
) -> dict:
    """Ask Decider to choose one of the available diagnostic actions."""

    payload = {
        "state": {
            "error": error,
            "evidence": evidence,
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

    with urlopen(request, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))

    answer = result["answers"]["next_action"]
    selected = answer["choice"]

    # Never execute an action that was not explicitly offered.
    if selected not in available_actions:
        raise ValueError(f"Decider returned an invalid action: {selected}")

    return {
        "action": selected,
        "probabilities": answer.get("probabilities", {}),
        "confidence": answer.get("confidence"),
        "model": result.get("model"),
    }
