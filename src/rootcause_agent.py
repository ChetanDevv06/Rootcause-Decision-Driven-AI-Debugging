from pathlib import Path

from strands import Agent, tool
from strands.models import BedrockModel

from src.diagnostics import inspect_dependencies


PROJECT_ROOT = Path(__file__).resolve().parent.parent


@tool
def inspect_project_dependencies() -> dict:
    """Inspect Python dependency files in the Rootcause project."""
    return inspect_dependencies(str(PROJECT_ROOT))


def build_agent() -> Agent:
    model = BedrockModel(
        model_id="amazon.nova-micro-v1:0",
        region_name="ap-southeast-2",
        temperature=0.1,
        max_tokens=500,
    )

    return Agent(
        model=model,
        tools=[inspect_project_dependencies],
        system_prompt=(
            "You are Rootcause, a software debugging agent. "
            "Use inspect_project_dependencies when dependency evidence "
            "would help investigate a Python error. "
            "Base conclusions on the evidence returned by tools. "
            "Never claim a tool ran if it did not."
        ),
    )


if __name__ == "__main__":
    agent = build_agent()

    result = agent(
        "Investigate whether this project's dependency files contain "
        "a declaration for psycopg. Inspect the files before concluding."
    )

    print("\n=== Rootcause investigation ===\n")
    print(result)