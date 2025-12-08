import requests

MODEL_NAME = "llama3.1:8b"


def ask_ollama(prompt: str) -> str:
    url = "http://localhost:11434/api/chat"

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "stream": False,
    }

    response = requests.post(url, json=payload)
    response.raise_for_status()

    data = response.json()

    return data["message"]["content"]


if __name__ == "__main__":
    question = "Напиши половину страницы научной фантастики"
    answer = ask_ollama(question)
    print("Вопрос:")
    print(question)
    print("\nОтвет модели:")
    print(answer)
