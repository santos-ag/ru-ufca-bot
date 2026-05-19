"""
Testes para o llm_cleaner.
"""

import json

import pytest


def _reset_llm_state(monkeypatch, llm_cleaner):
    monkeypatch.setattr(llm_cleaner, "_model_instance", None)
    monkeypatch.setattr(llm_cleaner, "_llm_configured", False)
    if hasattr(llm_cleaner, "_groq_client"):
        monkeypatch.setattr(llm_cleaner, "_groq_client", None)
    if hasattr(llm_cleaner, "_groq_configured"):
        monkeypatch.setattr(llm_cleaner, "_groq_configured", False)


def test_fallback_splits_prato_principal_by_comma(monkeypatch):
    from src.scraper import llm_cleaner

    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    _reset_llm_state(monkeypatch, llm_cleaner)

    raw_data = {"principal": "CARNE, FRANGO"}
    result = llm_cleaner.clean_meal_data_with_llm(raw_data)

    assert result["prato_principal"] == ["Carne", "Frango"]


def test_fallback_keeps_single_prato_principal_without_comma(monkeypatch):
    from src.scraper import llm_cleaner

    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    _reset_llm_state(monkeypatch, llm_cleaner)

    raw_data = {"principal": "CARNE ASSADA"}
    result = llm_cleaner.clean_meal_data_with_llm(raw_data)

    assert result["prato_principal"] == ["Carne Assada"]


def test_llm_output_prato_principal_is_normalized_by_comma(monkeypatch):
    from src.scraper import llm_cleaner

    class DummyResponse:
        text = json.dumps(
            {
                "prato_principal": "CARNE, FRANGO",
                "vegetariano": "",
                "acompanhamentos": [],
                "saladas": [],
                "suco": "",
                "sobremesa": "",
            }
        )

    class DummyModel:
        def generate_content(self, prompt):
            return DummyResponse()

    monkeypatch.setattr(llm_cleaner, "get_llm_model", lambda: DummyModel())

    raw_data = {"principal": "IGNORADO"}
    result = llm_cleaner.clean_meal_data_with_llm(raw_data)

    assert result["prato_principal"] == ["Carne", "Frango"]


def test_get_llm_model_uses_env_model_name(monkeypatch):
    from src.scraper import llm_cleaner

    monkeypatch.setenv("GOOGLE_API_KEY", "fake")
    monkeypatch.setenv("GOOGLE_MODEL", "gemini-2.0-flash")
    _reset_llm_state(monkeypatch, llm_cleaner)

    captured = {}

    def fake_configure(api_key):
        captured["api_key"] = api_key

    def fake_model(model_name, generation_config=None):
        captured["model_name"] = model_name
        captured["generation_config"] = generation_config
        return object()

    monkeypatch.setattr(llm_cleaner.genai, "configure", fake_configure)
    monkeypatch.setattr(llm_cleaner.genai, "GenerativeModel", fake_model)

    model = llm_cleaner.get_llm_model()

    assert model is not None
    assert captured["model_name"] == "gemini-2.0-flash"


def test_get_llm_model_uses_default_when_env_missing(monkeypatch):
    from src.scraper import llm_cleaner

    monkeypatch.setenv("GOOGLE_API_KEY", "fake")
    monkeypatch.delenv("GOOGLE_MODEL", raising=False)
    _reset_llm_state(monkeypatch, llm_cleaner)

    captured = {}

    def fake_configure(api_key):
        captured["api_key"] = api_key

    def fake_model(model_name, generation_config=None):
        captured["model_name"] = model_name
        captured["generation_config"] = generation_config
        return object()

    monkeypatch.setattr(llm_cleaner.genai, "configure", fake_configure)
    monkeypatch.setattr(llm_cleaner.genai, "GenerativeModel", fake_model)

    model = llm_cleaner.get_llm_model()

    assert model is not None
    assert captured["model_name"] == "gemini-2.0-flash"


def test_apply_groq_delay_sleeps_when_calls_are_close(monkeypatch):
    from src.scraper import llm_cleaner

    llm_cleaner._groq_last_call_ts = 100.0

    times = iter([100.1, 100.5])

    def fake_monotonic():
        return next(times)

    captured = {}

    def fake_sleep(value):
        captured["sleep"] = value

    monkeypatch.setattr(llm_cleaner, "_groq_delay_seconds", lambda: 0.5)
    monkeypatch.setattr(llm_cleaner.time, "monotonic", fake_monotonic)
    monkeypatch.setattr(llm_cleaner.time, "sleep", fake_sleep)

    llm_cleaner._apply_groq_delay()

    assert captured["sleep"] == pytest.approx(0.4, abs=0.001)
    assert llm_cleaner._groq_last_call_ts == pytest.approx(100.5, abs=0.001)


def test_parse_json_response_handles_trailing_text():
    from src.scraper import llm_cleaner

    text = '{"prato_principal": "CARNE"}\nExtra texto'
    result = llm_cleaner._parse_json_response(text)

    assert result == {"prato_principal": "CARNE"}


def test_parse_json_response_handles_multiple_json_objects():
    from src.scraper import llm_cleaner

    text = '{"prato_principal": "CARNE"}{"outra": "coisa"}'
    result = llm_cleaner._parse_json_response(text)

    assert result == {"prato_principal": "CARNE"}


def test_groq_provider_uses_env_model(monkeypatch):
    from src.scraper import llm_cleaner

    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "fake")
    monkeypatch.setenv("GROQ_MODEL", "llama-3.1-70b-versatile")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    captured = {}

    class DummyMessage:
        content = json.dumps(
            {
                "prato_principal": "CARNE, FRANGO",
                "vegetariano": "",
                "acompanhamentos": [],
                "saladas": [],
                "suco": "",
                "sobremesa": "",
            }
        )

    class DummyChoice:
        message = DummyMessage()

    class DummyResponse:
        choices = [DummyChoice()]

    class DummyCompletions:
        def create(self, model, messages, temperature, response_format=None):
            captured["model"] = model
            captured["messages"] = messages
            captured["temperature"] = temperature
            captured["response_format"] = response_format
            return DummyResponse()

    class DummyChat:
        completions = DummyCompletions()

    class DummyClient:
        chat = DummyChat()

    monkeypatch.setattr(llm_cleaner, "get_groq_client", lambda: DummyClient())

    raw_data = {"principal": "IGNORADO"}
    result = llm_cleaner.clean_meal_data_with_llm(raw_data)

    assert captured["model"] == "llama-3.1-70b-versatile"
    assert captured["response_format"] == {"type": "json_object"}
    assert captured["messages"][0]["role"] == "system"
    assert result["prato_principal"] == ["Carne", "Frango"]


def test_groq_provider_uses_default_model_when_env_missing(monkeypatch):
    from src.scraper import llm_cleaner

    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "fake")
    monkeypatch.delenv("GROQ_MODEL", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    captured = {}

    class DummyMessage:
        content = json.dumps(
            {
                "prato_principal": "CARNE",
                "vegetariano": "",
                "acompanhamentos": [],
                "saladas": [],
                "suco": "",
                "sobremesa": "",
            }
        )

    class DummyChoice:
        message = DummyMessage()

    class DummyResponse:
        choices = [DummyChoice()]

    class DummyCompletions:
        def create(self, model, messages, temperature, response_format=None):
            captured["model"] = model
            captured["response_format"] = response_format
            return DummyResponse()

    class DummyChat:
        completions = DummyCompletions()

    class DummyClient:
        chat = DummyChat()

    monkeypatch.setattr(llm_cleaner, "get_groq_client", lambda: DummyClient())

    raw_data = {"principal": "IGNORADO"}
    result = llm_cleaner.clean_meal_data_with_llm(raw_data)

    assert captured["model"] == "llama-3.1-8b-instant"
    assert captured["response_format"] == {"type": "json_object"}
    assert result["prato_principal"] == ["Carne"]
