import os
from openai import OpenAI
from dotenv import load_dotenv


def main():
    load_dotenv()

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    prompt = "Напиши короткое поздравление с днем рождения"
    temperatures = [0, 1, 1.8]

    for temp in temperatures:
        print(f"\n{'=' * 50}")
        print(f"Температура: {temp}")
        print('=' * 50)

        response = client.responses.create(
            model="gpt-4.1",
            input=prompt,
            temperature=temp,
        )

        # Parse response
        message = response.output[0]
        content = message.content[0].text

        print(content)
        print()


if __name__ == "__main__":
    main()
