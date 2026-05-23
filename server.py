#!/usr/bin/env python3
"""Local I Ching server with an Ollama interpretation endpoint."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")


def compact_text(value: Any, limit: int = 1800) -> str:
    text = str(value or "").strip()
    return text if len(text) <= limit else text[:limit].rstrip() + "..."


def hexagram_block(hexagram: dict[str, Any] | None) -> str:
    if not hexagram:
        return "None"
    lines = "\n".join(
        f"- Line {i + 1}: {compact_text(line, 360)}"
        for i, line in enumerate(hexagram.get("selectedLines", []))
    )
    if not lines:
        lines = "- No moving lines selected."
    return "\n".join(
        [
            f"{hexagram.get('id')}. {hexagram.get('ename')} / {hexagram.get('cname')} ({hexagram.get('cename', '')})",
            f"Judgment: {compact_text(hexagram.get('judgment'))}",
            f"Image: {compact_text(hexagram.get('image'))}",
            f"Commentary: {compact_text(hexagram.get('commentary'), 1200)}",
            "Moving line text:",
            lines,
        ]
    )


def build_messages(payload: dict[str, Any]) -> list[dict[str, str]]:
    question = compact_text(payload.get("question") or "No question entered.", 600)
    changing = payload.get("changing") or []
    transformed = payload.get("transformed")
    context = "\n\n".join(
        [
            f"Question: {question}",
            f"Method: {payload.get('method') or 'Unknown'}",
            f"Line numbers, bottom to top: {payload.get('lineNums')}",
            f"Moving lines, one-based: {[int(i) + 1 for i in changing]}",
            "Primary hexagram:",
            hexagram_block(payload.get("primary")),
            "Relating/transformed hexagram:",
            hexagram_block(transformed),
        ]
    )
    return [
        {
            "role": "system",
            "content": (
                "You interpret I Ching readings. Be grounded in the supplied hexagram text, "
                "practical, concise, and non-fatalistic. Do not claim certainty or predict the future. "
                "Use the question, primary hexagram, moving lines, and transformed hexagram. "
                "Write in warm plain English with short sections."
            ),
        },
        {
            "role": "user",
            "content": (
                context
                + "\n\nReturn exactly these sections:\n"
                + "Theme\nWhat It Suggests\nMoving Lines\nPractical Counsel\nReflection Question"
            ),
        },
    ]


def ask_ollama(payload: dict[str, Any]) -> dict[str, Any]:
    model = compact_text(payload.get("model") or DEFAULT_MODEL, 120)
    data = json.dumps(
        {
            "model": model,
            "messages": build_messages(payload),
            "stream": False,
            "options": {"temperature": 0.55, "num_predict": 650},
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{OLLAMA_HOST}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Ollama returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach Ollama at {OLLAMA_HOST}: {exc.reason}") from exc

    content = ((result.get("message") or {}).get("content") or "").strip()
    if not content:
        raise RuntimeError("Ollama returned an empty interpretation.")
    return {"model": model, "interpretation": content}


class IChingHandler(SimpleHTTPRequestHandler):
    def is_forbidden_path(self) -> bool:
        path = urllib.parse.unquote(urllib.parse.urlparse(self.path).path)
        return any(part.startswith(".") for part in path.split("/") if part)

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.end_headers()

    def do_GET(self) -> None:
        if self.is_forbidden_path():
            self.send_error(404, "File not found")
            return
        if self.path == "/api/health":
            self.send_json({"ok": True, "ollamaHost": OLLAMA_HOST, "defaultModel": DEFAULT_MODEL})
            return
        super().do_GET()

    def do_HEAD(self) -> None:
        if self.is_forbidden_path():
            self.send_error(404, "File not found")
            return
        super().do_HEAD()

    def do_POST(self) -> None:
        if self.path != "/api/interpret":
            self.send_error(404, "Unknown endpoint")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            self.send_json(ask_ollama(payload))
        except Exception as exc:
            self.send_json({"error": str(exc)}, status=502)

    def send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the I Ching app with an Ollama backend.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), IChingHandler)
    print(f"Serving http://{args.host}:{args.port}/")
    print(f"Ollama endpoint: {OLLAMA_HOST}/api/chat")
    print(f"Default model: {DEFAULT_MODEL}")
    server.serve_forever()


if __name__ == "__main__":
    main()
