from __future__ import annotations

import json
from io import BytesIO
from urllib.error import URLError

import pytest

from app.chat_runtime.contracts import DispatchRequest, InvocationKind, OCSBinding
from app.chat_runtime.host_adapters import HostAdapterError, HttpHostAdapter


def _binding() -> OCSBinding:
    return OCSBinding(
        ocs_id="DEDALA",
        instance_id="runtime:dedala:1",
        generation=3,
        authority_ref="authority:dedala:mission",
        state_namespace="state:dedala",
        memory_namespace="memory:dedala",
        host="GPT",
    )


def _request(parent: OCSBinding) -> DispatchRequest:
    return DispatchRequest(
        mission_id="mission:test:http-adapter",
        parent=parent,
        target_ocs_id="DEDALA",
        invocation_kind=InvocationKind.PEER_OCS,
        payload={"task": "review"},
        idempotency_key="test-key",
        requested_host="GPT",
    )


class _Response(BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False


def test_http_adapter_returns_bound_receipt(monkeypatch):
    target = _binding()
    request = _request(target)
    expected = {
        "mission_id": request.mission_id,
        "target_ocs_id": target.ocs_id,
        "target_instance_id": target.instance_id,
        "generation": target.generation,
        "host": target.host,
        "correlation_id": "dispatch:test",
        "output": {"verdict": "PASS"},
    }

    def fake_urlopen(req, timeout):
        assert req.get_header("Authorization") == "Bearer secret"
        assert timeout == 5.0
        return _Response(json.dumps(expected).encode("utf-8"))

    monkeypatch.setattr("app.chat_runtime.host_adapters.urlopen", fake_urlopen)
    adapter = HttpHostAdapter(endpoint="https://runtime.example/invoke", bearer_token="secret", timeout_seconds=5)
    receipt = adapter.invoke(request, target, "dispatch:test")
    assert receipt.target_ocs_id == "DEDALA"
    assert receipt.output == {"verdict": "PASS"}


def test_http_adapter_transport_failure_is_fail_closed(monkeypatch):
    target = _binding()
    request = _request(target)

    def fake_urlopen(req, timeout):
        raise URLError("offline")

    monkeypatch.setattr("app.chat_runtime.host_adapters.urlopen", fake_urlopen)
    adapter = HttpHostAdapter(endpoint="https://runtime.example/invoke")
    with pytest.raises(HostAdapterError, match="host_adapter_transport_failure"):
        adapter.invoke(request, target, "dispatch:test")


def test_http_adapter_rejects_invalid_receipt(monkeypatch):
    target = _binding()
    request = _request(target)

    def fake_urlopen(req, timeout):
        return _Response(b'{"output": []}')

    monkeypatch.setattr("app.chat_runtime.host_adapters.urlopen", fake_urlopen)
    adapter = HttpHostAdapter(endpoint="https://runtime.example/invoke")
    with pytest.raises(HostAdapterError, match="host_adapter_receipt_invalid"):
        adapter.invoke(request, target, "dispatch:test")
