# LLM Parameter Playground

An offline, single-file web app for playing with the sampling parameters of any
OpenAI-compatible endpoint — Ollama out of the box, or any custom base URL.
No API keys required, nothing leaves your machine, and every setting lives in
your browser's localStorage.

Built in the plain-English, step-by-step spirit of
[Dylan Asdale](https://dylanasdale.github.io) and
**Asdale Dynamics, LLC** — AI explained like a friend would.

## What it does

- **Temperature and top-p sliders** — drag either slider and the app
  automatically re-runs your saved prompt with the new value (about 0.6 s
  after you stop dragging), so you can *see* the effect instantly. Auto-run
  can be turned off if you'd rather press the button yourself.
- **System-prompt variants side by side** — keep up to 8 system prompts in
  labeled columns. One click (or one slider move) sends the same user prompt
  with the same parameters to every variant, then shows all the answers
  next to each other.
- **Seed and max-token controls** — set a seed for repeatable runs, or leave
  it blank for a fresh sample every time. Cap output length with max tokens.
- **Preset export / import** — one JSON file captures your prompt, variants,
  parameter values, base URL and model name. Share it, back it up, or load it
  on another machine. Import validates and normalizes everything, so a
  hand-edited file can't corrupt your setup.
- **Everything is saved locally** — endpoint, model, prompt, variants and
  parameters persist in localStorage. No accounts, no telemetry, no server.

## Quick start (Ollama)

1. Start Ollama with its OpenAI-compatible API:
   ```
   ollama serve
   ollama pull llama3.2
   ```
2. Open `index.html` in your browser (double-click it, or `python3 -m http.server`
   and visit `http://localhost:8000/index.html`).
3. The defaults already point at `http://localhost:11434/v1` with model
   `llama3.2`. Click **Test connection** — you should see your model list.
4. Type a prompt, then hit **Run all variants**. Move the temperature slider
   and watch the answers rewrite themselves while the seed stays fixed.

## Any other OpenAI-compatible server

Point **Base URL** at any server that implements `/chat/completions`
(LM Studio, llama.cpp server, vLLM, OpenRouter, whatever you run). The URL
should end in `/v1`, e.g. `http://localhost:1234/v1` for LM Studio. The app
sends a standard `POST {base}/chat/completions` request.

An optional API-key box is there for servers that want one, but it is never
required, never exported in presets, and never leaves your browser.

## Presets

- **Export preset JSON** downloads a `llm-parameter-playground-preset.json`
  file with: base URL, model, prompt, all system-prompt variants, temperature,
  top-p, seed and max tokens.
- **Import preset JSON** takes a pasted or file-loaded JSON — either a full
  exported file or just the inner `preset` object. Out-of-range numbers are
  clamped back into slider range (temperature 0–2, top-p 0–1), so presets
  made elsewhere stay safe.

## Tests

The pure logic (slider math, request building, preset export/import) ships
inside `index.html` between `CORE-BEGIN`/`CORE-END` markers, and the test
suite runs that exact code — no reimplementation drift.

Requires Python 3 and node:

```
pytest tests/
```

## Files

| File | What it is |
| --- | --- |
| `index.html` | The whole app — no build step, no dependencies |
| `tests/test_core.py` | pytest suite for slider math and preset export/import |
| `README.md` | This file |
| `LICENSE` | MIT license, Copyright (c) 2026 Asdale Dynamics, LLC |
| `STATUS.md` | What was built, how it was verified, known gaps |

## License

MIT — see [LICENSE](LICENSE). © 2026 Asdale Dynamics, LLC
