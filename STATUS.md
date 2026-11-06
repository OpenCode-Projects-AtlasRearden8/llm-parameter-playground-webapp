# STATUS — LLM Parameter Playground

Last updated: 2026-11-06

## What was built

`index.html` — an offline, single-file web app (no build step, no
dependencies) for exploring LLM sampling parameters against any
OpenAI-compatible endpoint:

- **Temperature slider (0–2) and top-p slider (0–1)** — values snap to the
  0.01 slider step with visible numeric readouts; changes auto re-run the
  saved prompt ~0.6 s after you stop dragging (auto-run toggle included),
  so you see the effect of each parameter instantly.
- **One saved prompt** — a single textarea, autosaved to localStorage after
  every keystroke.
- **System-prompt variants side by side** — up to 8 labeled columns; each
  run sends the same user prompt + parameters to every variant and renders
  all answers in parallel, per-column, with per-column errors and token
  usage. Run/Stop buttons use AbortController so nothing hangs.
- **Seed and max-token controls** — seed blank = random every run; filled =
  `seed` field sent to the API for repeatable comparisons. Max tokens
  clamped to ≥ 1, sent as both `max_tokens` and `max_completion_tokens`
  for compatibility across servers.
- **Preset export/import JSON** — export downloads the full state (base
  URL, model, prompt, variants, temperature, top-p, seed, max tokens);
  import accepts pasted JSON or a file, validates structure, rejects
  foreign apps, clamps out-of-range slider values, and normalizes missing
  fields. API keys are stored separately and never exported.
- **Connection helper** — "Test connection" hits `{base}/models` and lists
  available model IDs; status feedback is inline.
- **Everything persists in localStorage** (schema-keyed
  `llm-parameter-playground-state-v1`; corrupt storage falls back to
  defaults instead of crashing).

Default endpoint is `http://localhost:11434/v1` (Ollama); any other
OpenAI-compatible base URL works. Optional API-key field for servers that
require one; nothing is ever required, sent anywhere else, or exported.

## Attribution

Built by **Asdale Dynamics, LLC** (Dylan Asdale) — beginner-friendly AI
education, in the plain-English style of dylanasdale.github.io.
MIT licensed: `LICENSE` contains exactly
`Copyright (c) 2026 Asdale Dynamics, LLC`.

## How to run it

- Open `index.html` in any modern browser (file:// works; no server
  needed). Or serve it: `python3 -m http.server` and open
  `http://localhost:8000/index.html`.
- Against Ollama: run `ollama serve`, `ollama pull llama3.2` (or your
  model), keep the default base URL, click **Test connection**, then
  **Run all variants**.

## Verification results

- `pytest tests/` — **28 passed**. Tests extract the `CORE-BEGIN` /
  `CORE-END` block from the shipped `index.html` and run it through node,
  so they exercise the exact code users get (no unreferenced duplicate).
  Coverage: slider math (clamping, step-snapping, bad-input fallbacks),
  request payload shape (messages, both max-token fields, seed omission),
  headers (Bearer only when a key is set), base-URL normalization,
  preset export shape/normalization/8-variant cap, preset round trip, and
  import validation (bad JSON, non-object, foreign app, bare preset,
  missing fields).
- `node --check` on the full inline script — passes (valid classic
  browser JS).
- End-to-end request smoke test against a mock OpenAI server
  (`GET /v1/models` and `POST /v1/chat/completions`) — the app's real
  request path (core-built URL, headers, payload) returned 200 with the
  expected completion content and usage.
- DOM-level runtime smoke test (node `vm` + stubbed `document` /
  `localStorage`): `hydrate()`, `connectControls()`, `renderVariants()`,
  `saveState()`, `loadState()` and the corrupt-storage fallback all ran
  without errors, and the persisted shape was verified (app id,
  normalized params, autoRun, separate apiKey storage, variants array).
- Committed to the local repo only (`663dc0b`). Nothing pushed, no
  remotes, nothing published.

## Known gaps

- No streaming — results appear when each request completes; very long
  max-token runs can feel slow.
- No response-diff/side-by-side highlight of similarities; outputs are
  plain text.
- No browser-automation test (Playwright-style); UI runtime is covered by
  the stub-DOM smoke test plus manual use instead.
- Runs are sequential per column but capped by browser connection limits
  per origin — with 8 variants on one endpoint, HTTP/1.1 keep-alive may
  briefly serialize requests.
- Presets are plain JSON files with no schema versioning policy beyond
  `version: 1`; future format changes will need a migration path.
- API-key input is stored in localStorage (clearly separate, never
  exported) but is not encrypted — normal browser-storage tradeoff, only
  relevant for hosted endpoints; Ollama-style local use needs no key.
