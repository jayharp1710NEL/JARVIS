import pytest

from app.config import get_settings
from app.models.base import GenSettings, extract_json
from app.models.fake import FakeProvider
from app.models.optional_cloud import CloudDisabledError, OptionalCloudProvider
from app.models.router import build_provider
from app.agent.schemas import Message, Role


def test_fake_provider_generates():
    fp = FakeProvider()
    out = fp.generate([Message(role=Role.user, content="ping")], GenSettings())
    assert "ping" in out
    assert fp.health_check().ok


def test_fake_provider_scripted():
    fp = FakeProvider().script("weather", "It is sunny.")
    out = fp.generate([Message(role=Role.user, content="what's the weather?")], GenSettings())
    assert out == "It is sunny."


def test_extract_json_variants():
    assert extract_json('{"a": 1}') == {"a": 1}
    assert extract_json('here you go:\n```json\n{"b": 2}\n```') == {"b": 2}
    assert extract_json('prefix {"c": [1,2]} suffix') == {"c": [1, 2]}
    with pytest.raises(ValueError):
        extract_json("no json here")


def test_cloud_disabled_by_default():
    settings = get_settings()
    assert settings.enable_cloud_mode is False
    with pytest.raises(CloudDisabledError):
        OptionalCloudProvider(settings)
    with pytest.raises(CloudDisabledError):
        build_provider("cloud", settings)


def test_build_known_providers():
    settings = get_settings()
    assert build_provider("ollama", settings).name == "ollama"
    assert build_provider("openai_compatible", settings).name == "openai_compatible"
    with pytest.raises(ValueError):
        build_provider("does-not-exist", settings)


def test_ollama_health_clear_error_when_down():
    settings = get_settings()
    prov = build_provider("ollama", settings)
    status = prov.health_check()
    # Not running in tests; must report a clear, non-crashing status.
    assert status.ok is False
    assert "Ollama" in status.detail
