import requests, os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DEV_ASSISTANT_GITHUB_TOKEN")  # сюда положи тот же токен, что сейчас тестил
OWNER = "olegalibekov"
REPO = "rag_check"
ISSUE_OR_PR_NUMBER = 1  # сюда реальный номер PR/issue

url = f"https://api.github.com/repos/{OWNER}/{REPO}/issues/{ISSUE_OR_PR_NUMBER}/comments"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}

data = {"body": "Test comment from tmp_comment.py"}

resp = requests.post(url, headers=headers, json=data)

print("Status:", resp.status_code)
print("X-OAuth-Scopes:", resp.headers.get("X-OAuth-Scopes"))
print("X-Accepted-OAuth-Scopes:", resp.headers.get("X-Accepted-OAuth-Scopes"))
print("Body:", resp.text)
