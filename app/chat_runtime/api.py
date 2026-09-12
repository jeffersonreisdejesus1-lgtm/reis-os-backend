from __future__ import annotations

import json
import os
from dataclasses import asdict

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from .contracts import DispatchRequest, InvocationKind, OCSBinding
from .host_adapters import HttpHostAdapter
from .runtime import ReisOSChatRuntime

router = APIRouter(prefix="/internal/chat-runtime", tags=["chat-runtime"])


class ParentBindingIn(BaseModel):
    ocs_id: str
    instance_id: str
    generation: int = Field(ge=0)
    authority_ref: str
    state_namespace: str
    memory_namespace: str
    host: str


class DispatchIn(BaseModel):
    mission_id: str
    parent: ParentBindingIn
    target_ocs_id: str
    invocation_kind: InvocationKind
    payload: dict[str, object]
    idempotency_key: str
    requested_host: str | None = None


def _load_bindings() -> dict[str, OCSBinding]:
    raw = os.getenv("REIS_CHAT_BINDINGS_JSON", "{}")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("chat_bindings_invalid")
    result: dict[str, OCSBinding] = {}
    for ocs_id, item in data.items():
        if not isinstance(item, dict):
            raise ValueError("chat_binding_invalid")
        result[str(ocs_id)] = OCSBinding(
            ocs_id=str(item["ocs_id"]),
            instance_id=str(item["instance_id"]),
            generation=int(item["generation"]),
            authority_ref=str(item["authority_ref"]),
            state_namespace=str(item["state_namespace"]),
            memory_namespace=str(item["memory_namespace"]),
            host=str(item["host"]),
        )
    return result


def _load_adapters() -> dict[str, HttpHostAdapter]:
    raw = os.getenv("REIS_CHAT_HOSTS_JSON", "{}")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("chat_hosts_invalid")
    result: dict[str, HttpHostAdapter] = {}
    for host, item in data.items():
        if not isinstance(item, dict) or not item.get("endpoint"):
            raise ValueError("chat_host_invalid")
        token_env = item.get("token_env")
        token = os.getenv(str(token_env)) if token_env else None
        result[str(host)] = HttpHostAdapter(
            endpoint=str(item["endpoint"]),
            bearer_token=token,
            timeout_seconds=float(item.get("timeout_seconds", 30.0)),
        )
    return result


def _authority_policy(parent: OCSBinding, target: OCSBinding, kind: InvocationKind) -> bool:
    allowed_raw = os.getenv("REIS_CHAT_AUTHORITY_EDGES_JSON", "[]")
    allowed = json.loads(allowed_raw)
    edge = f"{parent.ocs_id}->{target.ocs_id}:{kind.value}"
    return edge in allowed


def _check_internal_token(authorization: str | None) -> None:
    expected = os.getenv("REIS_CHAT_RUNTIME_TOKEN")
    if not expected:
        raise HTTPException(status_code=503, detail="chat_runtime_token_unconfigured")
    if authorization != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="chat_runtime_unauthorized")


@router.get("/readiness")
def readiness() -> dict[str, object]:
    try:
        bindings = _load_bindings()
        adapters = _load_adapters()
        authority_edges = json.loads(os.getenv("REIS_CHAT_AUTHORITY_EDGES_JSON", "[]"))
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return {"status": "HOLD", "reason": "chat_runtime_configuration_invalid"}
    if not bindings:
        return {"status": "HOLD", "reason": "bindings_unconfigured"}
    if not adapters:
        return {"status": "HOLD", "reason": "host_adapters_unconfigured"}
    if not authority_edges:
        return {"status": "HOLD", "reason": "authority_edges_unconfigured"}
    if not os.getenv("REIS_CHAT_RUNTIME_TOKEN"):
        return {"status": "HOLD", "reason": "chat_runtime_token_unconfigured"}
    return {
        "status": "READY",
        "bindings": sorted(bindings),
        "hosts": sorted(adapters),
        "authority_edge_count": len(authority_edges),
    }


@router.post("/dispatch")
def dispatch(body: DispatchIn, authorization: str | None = Header(default=None)) -> dict[str, object]:
    _check_internal_token(authorization)
    try:
        bindings = _load_bindings()
        adapters = _load_adapters()
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=503, detail="chat_runtime_configuration_invalid") from exc

    runtime = ReisOSChatRuntime(
        bindings=bindings,
        host_adapters=adapters,
        authority_policy=_authority_policy,
    )
    parent = OCSBinding(**body.parent.model_dump())
    receipt = runtime.dispatch(
        DispatchRequest(
            mission_id=body.mission_id,
            parent=parent,
            target_ocs_id=body.target_ocs_id,
            invocation_kind=body.invocation_kind,
            payload=body.payload,
            idempotency_key=body.idempotency_key,
            requested_host=body.requested_host,
        )
    )
    result = asdict(receipt)
    result["invocation_kind"] = receipt.invocation_kind.value
    result["outcome"] = receipt.outcome.value
    return result
