import json
import re
import subprocess
import tempfile
import threading
import functools
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parent.parent
INDEX = PROJECT / "index.html"


@functools.lru_cache(maxsize=None)
def _core_js() -> str:
    """Extract the CORE block shipped inside index.html (the real code users get)."""
    html = INDEX.read_text(encoding="utf-8")
    match = re.search(r"/\* CORE-BEGIN \*/(.*?)/\* CORE-END \*/", html, re.DOTALL)
    assert match, "CORE block not found in index.html"
    return match.group(1)


NODE_LOCK = threading.Lock()


def _run_node(script: str) -> str:
    with NODE_LOCK:
        proc = subprocess.run(
            ["node", "-e", script],
            capture_output=True,
            text=True,
            timeout=30,
        )
    assert proc.returncode == 0, f"node failed:\n{proc.stderr}"
    return proc.stdout


class CoreHarness:
    def __init__(self, core_path: Path):
        self.core_path = core_path

    def eval(self, expr: str):
        script = (
            f"const CORE = require({json.dumps(str(self.core_path))});\n"
            f"const result = ({expr});\n"
            "process.stdout.write(JSON.stringify(result === undefined ? null : result));\n"
        )
        return json.loads(_run_node(script))


@pytest.fixture(scope="session")
def core(tmp_path_factory):
    d = tmp_path_factory.mktemp("corejs")
    path = d / "core.js"
    path.write_text(_core_js(), encoding="utf-8")
    return CoreHarness(path)


def test_app_script_is_valid_browser_script(tmp_path):
    """The entire inline <script> must parse as classic (non-module) JS."""
    html = INDEX.read_text(encoding="utf-8")
    match = re.search(r"<script>(.*?)</script>", html, re.DOTALL)
    script = match.group(1)
    js = tmp_path / "app.js"
    js.write_text(script, encoding="utf-8")
    proc = subprocess.run(["node", "--check", str(js)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert "CORE-BEGIN" in script and "CORE-END" in script


def test_license_and_attribution():
    license_text = (PROJECT / "LICENSE").read_text(encoding="utf-8")
    assert "Copyright (c) 2026 Asdale Dynamics, LLC" in license_text
    assert license_text.lstrip().startswith("MIT License")
    readme = (PROJECT / "README.md").read_text(encoding="utf-8")
    assert "Asdale Dynamics, LLC" in readme


# ---------- slider math ----------

def test_temperature_clamped_to_range(core):
    assert core.eval("CORE.normalizeTemperature(-0.5)") == 0.0
    assert core.eval("CORE.normalizeTemperature(3.7)") == 2.0
    assert core.eval("CORE.normalizeTemperature(0.5)") == 0.5


def test_temperature_snaps_to_slider_step(core):
    assert core.eval("CORE.normalizeTemperature(0.336)") == pytest.approx(0.34)
    assert core.eval("CORE.normalizeTemperature(1.234)") == pytest.approx(1.23)


def test_temperature_rejects_non_numbers(core):
    assert core.eval("CORE.normalizeTemperature('banana')") == 0.0
    assert core.eval("CORE.normalizeTemperature(null)") == 0.0


def test_top_p_clamped_to_unit_interval(core):
    assert core.eval("CORE.normalizeTopP(-2)") == 0.0
    assert core.eval("CORE.normalizeTopP(1.6)") == 1.0
    assert core.eval("CORE.normalizeTopP(0.9999)") == pytest.approx(1.0)


def test_top_p_snaps_to_slider_step(core):
    assert core.eval("CORE.normalizeTopP(0.554)") == pytest.approx(0.55)


def test_max_tokens_falls_back_on_bad_values(core):
    assert core.eval("CORE.normalizeMaxTokens(-5, 256)") == 256
    assert core.eval("CORE.normalizeMaxTokens(0, 256)") == 256
    assert core.eval("CORE.normalizeMaxTokens('', 256)") == 256
    assert core.eval("CORE.normalizeMaxTokens('12.7', 256)") == 13


def test_max_tokens_keeps_positive_values(core):
    assert core.eval("CORE.normalizeMaxTokens(64, 256)") == 64
    assert core.eval("CORE.normalizeMaxTokens('4096', 256)") == 4096


def test_seed_blank_means_random(core):
    assert core.eval("CORE.normalizeSeed('')") is None
    assert core.eval("CORE.normalizeSeed(null)") is None
    assert core.eval("CORE.normalizeSeed('not-a-seed')") is None


def test_seed_integer_rounded(core):
    assert core.eval("CORE.normalizeSeed('42')") == 42
    assert core.eval("CORE.normalizeSeed(7.9)") == 8
    assert core.eval("CORE.normalizeSeed(-1)") == -1


# ---------- request building ----------

def test_request_payload_shape(core):
    body = core.eval(
        "CORE.buildRequestParams({prompt: 'hi', system: 'sys', temperature: 0.5,"
        " topP: 0.9, seed: 7, maxTokens: 128, model: 'llama3.2'})"
    )
    assert body["model"] == "llama3.2"
    assert body["messages"][0] == {"role": "system", "content": "sys"}
    assert body["messages"][1] == {"role": "user", "content": "hi"}
    assert body["temperature"] == 0.5
    assert body["top_p"] == pytest.approx(0.9)
    assert body["max_tokens"] == 128
    assert body["max_completion_tokens"] == 128
    assert body["seed"] == 7


def test_request_payload_omits_seed_when_random(core):
    body = core.eval("CORE.buildRequestParams({prompt: 'hi', system: 'sys', seed: null})")
    assert "seed" not in body


def test_request_payload_missing_sliders_fall_to_lower_bounds(core):
    body = core.eval("CORE.buildRequestParams({prompt: 'hi', system: ''})")
    assert body["temperature"] == 0.0
    assert body["top_p"] == 0.0
    assert body["max_tokens"] == 256
    assert body["model"] == "llama3.2"


def test_request_payload_normalizes_out_of_range_sliders(core):
    body = core.eval(
        "CORE.buildRequestParams({prompt: 'p', system: '', temperature: 42, topP: -3, model: ' x '})"
    )
    assert body["temperature"] == 2.0
    assert body["top_p"] == 0.0
    assert body["model"] == "x"


def test_headers_no_authorization_without_key(core):
    headers = core.eval("CORE.buildHeaders({})")
    assert headers == {"Content-Type": "application/json"}
    headers = core.eval("CORE.buildHeaders({apiKey: '   '})")
    assert "Authorization" not in headers


def test_headers_bearer_with_key(core):
    headers = core.eval("CORE.buildHeaders({apiKey: 'sk-nope'})")
    assert headers["Authorization"] == "Bearer sk-nope"


def test_chat_completions_url(core):
    assert core.eval(
        "CORE.chatCompletionsUrl('http://localhost:11434/v1/')"
    ) == "http://localhost:11434/v1/chat/completions"


def test_base_url_default(core):
    assert core.eval("CORE.normalizeBaseUrl('')") == "http://localhost:11434/v1"
    assert core.eval("CORE.normalizeBaseUrl('   ')") == "http://localhost:11434/v1"


# ---------- preset export ----------

def test_serialize_preset_shape(core):
    text = core.eval(
        "CORE.serializePreset({baseUrl: 'http://localhost:11434/v1', model: 'm1',"
        " prompt: 'p', variants: [{name: 'A', text: 'sa'}, {name: 'B', text: ''}],"
        " params: {temperature: 1, topP: 1, seed: 3, maxTokens: 64}})"
    )
    data = json.loads(text)
    assert data["app"] == "llm-parameter-playground"
    assert data["version"] == 1
    assert data["preset"]["model"] == "m1"
    assert data["preset"]["prompt"] == "p"
    assert data["preset"]["variants"] == [{"name": "A", "text": "sa"}, {"name": "B", "text": ""}]
    assert data["preset"]["params"] == {
        "temperature": 1.0,
        "topP": 1.0,
        "seed": 3,
        "maxTokens": 64,
    }


def test_serialize_preset_normalizes_bad_slider_values(core):
    data = json.loads(core.eval(
        "CORE.serializePreset({model: 'm', prompt: '', variants: [],"
        " params: {temperature: 99, topP: -1, seed: 'x', maxTokens: -9}})"
    ))
    assert data["preset"]["params"]["temperature"] == 2.0
    assert data["preset"]["params"]["topP"] == 0.0
    assert data["preset"]["params"]["seed"] is None
    assert data["preset"]["params"]["maxTokens"] == 256


def test_serialize_preset_caps_variants_at_eight(core):
    text = core.eval(
        "CORE.serializePreset({model: 'm', prompt: '',"
        " variants: Array.from({length: 12}, (_, i) => ({name: 'v' + i, text: ''})),"
        " params: {temperature: 0, topP: 1}})"
    )
    data = json.loads(text)
    assert len(data["preset"]["variants"]) == 8
    assert data["preset"]["variants"][0]["name"] == "v0"


def test_preset_round_trip(core):
    text = core.eval(
        "CORE.serializePreset({baseUrl: 'http://x/v1', model: 'qwen', prompt: 'hello',"
        " variants: [{name: 'A', text: 'be terse'}],"
        " params: {temperature: 0.42, topP: 0.77, seed: 99, maxTokens: 512}})"
    )
    back = core.eval("CORE.parsePreset(" + json.dumps(text) + ")")
    assert back["ok"] is True
    data = back["data"]
    assert data["baseUrl"] == "http://x/v1"
    assert data["model"] == "qwen"
    assert data["prompt"] == "hello"
    assert data["variants"] == [{"name": "A", "text": "be terse"}]
    assert data["params"]["temperature"] == pytest.approx(0.42)
    assert data["params"]["topP"] == pytest.approx(0.77)
    assert data["params"]["seed"] == 99
    assert data["params"]["maxTokens"] == 512


# ---------- preset import ----------

def test_parse_preset_rejects_invalid_json(core):
    result = core.eval("CORE.parsePreset('{not json')")
    assert result["ok"] is False
    assert "JSON" in result["error"]


def test_parse_preset_rejects_non_object(core):
    result = core.eval("CORE.parsePreset('[1,2,3]')")
    assert result["ok"] is False


def test_parse_preset_rejects_foreign_app(core):
    result = core.eval("CORE.parsePreset('{\"app\":\"someone-elses-app\",\"preset\":{}}')")
    assert result["ok"] is False
    assert "different app" in result["error"]


def test_parse_preset_accepts_bare_preset_without_wrapper(core):
    result = core.eval(
        "CORE.parsePreset(JSON.stringify({baseUrl: 'http://localhost:1234/v1',"
        " model: 'mistral', prompt: 'p', variants: [{name: 'N', text: 'T'}],"
        " params: {temperature: 0.9, topP: 0.8, seed: null, maxTokens: 32}}))"
    )
    assert result["ok"] is True
    assert result["data"]["model"] == "mistral"
    assert result["data"]["params"]["maxTokens"] == 32


def test_parse_preset_fills_missing_fields_safely(core):
    result = core.eval("CORE.parsePreset(JSON.stringify({preset: {}}))")
    assert result["ok"] is True
    data = result["data"]
    assert data["baseUrl"] == "http://localhost:11434/v1"
    assert data["model"] == "llama3.2"
    assert data["prompt"] == ""
    assert data["params"]["maxTokens"] == 256
    assert data["params"]["seed"] is None
