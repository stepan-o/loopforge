import importlib
import os


def test_bool_from_env_true_false(monkeypatch):
    from loopforge import config as cfg
    # default false
    assert cfg._bool_from_env("NON_EXISTENT_FLAG", default=False) is False
    assert cfg._bool_from_env("NON_EXISTENT_FLAG", default=True) is True

    monkeypatch.setenv("FLAG_TRUE", "true")
    monkeypatch.setenv("FLAG_YES", "Yes")
    monkeypatch.setenv("FLAG_ONE", "1")
    monkeypatch.setenv("FLAG_ON", "on")

    assert cfg._bool_from_env("FLAG_TRUE", default=False) is True
    assert cfg._bool_from_env("FLAG_YES", default=False) is True
    assert cfg._bool_from_env("FLAG_ONE", default=False) is True
    assert cfg._bool_from_env("FLAG_ON", default=False) is True

    monkeypatch.setenv("FLAG_FALSE", "false")
    assert cfg._bool_from_env("FLAG_FALSE", default=True) is False


def test_config_flags_defaults(monkeypatch):
    # Clear env vars and reload module
    for key in ["USE_LLM_POLICY", "LLM_MODEL_NAME", "OPENAI_API_KEY"]:
        monkeypatch.delenv(key, raising=False)

    import loopforge.config as cfg
    importlib.reload(cfg)

    assert cfg.USE_LLM_POLICY is False
    assert isinstance(cfg.LLM_MODEL_NAME, str) and cfg.LLM_MODEL_NAME
    assert cfg.OPENAI_API_KEY is None


def test_config_flags_enabled(monkeypatch):
    monkeypatch.setenv("USE_LLM_POLICY", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("LLM_MODEL_NAME", "gpt-4.1-mini")

    import loopforge.config as cfg
    importlib.reload(cfg)

    assert cfg.USE_LLM_POLICY is True
    assert cfg.OPENAI_API_KEY == "sk-test"
    assert cfg.LLM_MODEL_NAME == "gpt-4.1-mini"
