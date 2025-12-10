#!/usr/bin/env python3
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.request

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2:3b"  # твоя модель


def ask_ollama(prompt: str) -> str:
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False
    }).encode("utf-8")

    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data["message"]["content"]


HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Local LLaMA</title>
</head>
<body>
<h1>Local LLaMA Chat</h1>
<input id="msg" type="text" placeholder="Введите сообщение" style="width:300px;">
<button onclick="send()">Отправить</button>

<pre id="response" style="white-space:pre-wrap; margin-top:20px;"></pre>

<script>
async function send() {
    const message = document.getElementById("msg").value;
    const resp = await fetch("/", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({message})
    });
    const data = await resp.json();
    document.getElementById("response").innerText = data.reply;
}
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # отдаём HTML страницу
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML_PAGE.encode("utf-8"))

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        data = json.loads(body.decode("utf-8"))

        prompt = data["message"]
        reply = ask_ollama(prompt)

        result = json.dumps({"reply": reply}).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(result)


def run():
    server = HTTPServer(("0.0.0.0", 8000), Handler)
    print("Browser chat running on: http://0.0.0.0:8000")
    server.serve_forever()


if __name__ == "__main__":
    run()
