import boto3
from botocore.exceptions import ClientError, NoCredentialsError

REGION = "ap-southeast-2"
MODEL_ID = "amazon.nova-micro-v1:0"


def main():
    try:
        client = boto3.client("bedrock-runtime", region_name=REGION)

        response = client.converse(
            modelId=MODEL_ID,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "text": (
                                "You are helping debug a Python application. "
                                "Given this error: "
                                "'ModuleNotFoundError: No module named psycopg', "
                                "provide the two most likely causes and one "
                                "safe diagnostic step. Keep it under 100 words."
                            )
                        }
                    ],
                }
            ],
            inferenceConfig={
                "maxTokens": 180,
                "temperature": 0.2,
            },
        )

        answer = response["output"]["message"]["content"]
        print("\n=== Bedrock response ===\n")

        for block in answer:
            if "text" in block:
                print(block["text"])

        usage = response.get("usage", {})
        print("\n=== Token usage ===")
        print(f"Input tokens:  {usage.get('inputTokens', 'N/A')}")
        print(f"Output tokens: {usage.get('outputTokens', 'N/A')}")

    except NoCredentialsError:
        print("AWS credentials were not found. Check your AWS CLI login.")
    except ClientError as exc:
        error = exc.response.get("Error", {})
        print(f"AWS error: {error.get('Code', 'Unknown')}")
        print(error.get("Message", str(exc)))


if __name__ == "__main__":
    main()