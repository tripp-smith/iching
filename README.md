# I Ching Oracle

A local I Ching consultation app with a lightweight Python backend and local Ollama interpretation.

## Run locally

```bash
python3 server.py
```

Open:

```text
http://127.0.0.1:8765/
```

## Run on your local network

```bash
python3 server.py --host 0.0.0.0 --port 8765
```

Then open this from another device on the same network:

```text
http://YOUR_MAC_IP:8765/
```

On macOS, find your local IP with:

```bash
ipconfig getifaddr en0
```

## Ollama

The app calls Ollama at `http://127.0.0.1:11434` by default and uses `llama3.1:8b` unless configured otherwise.

Override either setting with environment variables:

```bash
OLLAMA_HOST=http://127.0.0.1:11434 OLLAMA_MODEL=llama3.1:8b python3 server.py
```

Make sure the model is available:

```bash
ollama pull llama3.1:8b
```

## License

This project is licensed under the Apache License 2.0. See [LICENSE](LICENSE).
