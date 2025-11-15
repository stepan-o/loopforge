import importlib

import types


def test_chat_json_disabled(monkeypatch):
    # Force policy off or no key
    monkeypatch.setenv("USE_LLM_POLICY", "false")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    import loopforge.llm_client as lc
    importlib.reload(lc)

    # get_client should return None; chat_json returns None
    assert lc.get_client() is None
    out = lc.chat_json("system", [{"role": "user", "content": "hi"}], "schema")
    assert out is None


def test_chat_json_success(monkeypatch):
    # Enable policy and set fake key
    monkeypatch.setenv("USE_LLM_POLICY", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    import loopforge.llm_client as lc
    importlib.reload(lc)

    class FakeMsg:
        def __init__(self, content):
            self.content = content

    class Choice:
        def __init__(self, content):
            self.message = FakeMsg(content)

    class Completion:
        def __init__(self, content):
            self.choices = [Choice(content)]

    class Chat:
        def completions_create(self, **kwargs):
            return Completion('{"type": "work", "target": "line_a"}')

        # The SDK shape is client.chat.completions.create(...)
        class completions:
            @staticmethod
            def create(**kwargs):
                return Completion('{"type": "work", "target": "line_a"}')

    class FakeClient:
        def __init__(self):
            self.chat = types.SimpleNamespace(
                completions=types.SimpleNamespace(
                    create=lambda **kwargs: Completion('{"type": "work", "target": "line_a"}')
                )
            )

    # Monkeypatch get_client to return our fake
    monkeypatch.setattr(lc, "get_client", lambda: FakeClient())

    out = lc.chat_json("system", [{"role": "user", "content": "state"}], "schema")
    assert isinstance(out, dict)
    assert out.get("type") == "work"
    assert out.get("target") == "line_a"

def test_chat_json_non_json(monkeypatch):
    monkeypatch.setenv("USE_LLM_POLICY", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    import loopforge.llm_client as lc
    importlib.reload(lc)

    class FakeMsg:
        def __init__(self, content):
            self.content = content

    class Choice:
        def __init__(self, content):
            self.message = FakeMsg(content)

    class Completion:
        def __init__(self, content):
            self.choices = [Choice(content)]

    class FakeClient:
        def __init__(self):
            self.chat = types.SimpleNamespace(
                completions=types.SimpleNamespace(create=lambda **kwargs: Completion("not json"))
            )

    monkeypatch.setattr(lc, "get_client", lambda: FakeClient())

    out = lc.chat_json("sys", [{"role": "user", "content": "x"}], "schema")
    assert out is None
