from strands import Agent
from strands.models import BedrockModel

if __name__ == "__main__":
    model = BedrockModel(
        model_id="amazon.nova-micro-v1:0",
        region_name="ap-southeast-2",
        temperature=0.1,
        max_tokens=500,
    )

    agent = Agent(
        model=model,
        system_prompt=(
            "You are Rootcause, a concise software debugging assistant. "
            "Answer in at most 80 words. Do not use lengthy explanations."
        ),
    )

    response = agent(
        "For ModuleNotFoundError: No module named 'psycopg', "
        "give two likely causes and one diagnostic command. "
        "Keep the entire answer under 80 words."
    )

    print("\n=== Rootcause / Strands response ===\n")
    print(response)
