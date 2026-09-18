from __future__ import annotations

import asyncio
import json
import os
import secrets
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

PROGRAM_ID = "REIS-OS-ARTIFICIAL-BRAIN-VALIDATION-001"
AUTONOMOUS_GATES = frozenset({f"AB{i}" for i in range(6, 13)})
FORBIDDEN_CAPABILITIES = frozenset({"GITHUB_MERGE_PR", "FOUNDER_PROMOTION", "AB13_PROMOTION"})

router = APIRouter(prefix="/execution-bindings", tags=["execution-bindings"])


@dataclass(frozen=True)
class ProviderConfig:
    url: str
    token: str
    required_capability: str


class ExecutionEnvelope(BaseModel):
    program_id: str
    gate: str
    capability: str = Field(min_length=1)
    founder_approval_ref: str = Field(min_length=1)
    payload: dict[str, Any]


def _provider_config(kind: str) -> ProviderConfig:
    if kind == "authority":
        return ProviderConfig(
            url=os.getenv("REIS_APPROVED_HOST_EXECUTOR_URL", "").rstrip("/"),
            token=os.getenv("REIS_APPROVED_HOST_EXECUTOR_TOKEN", ""),
            required_capability="governed_effect_execution",
        )
    if kind == "implementation":
        return ProviderConfig(
            url=os.getenv("REIS_IMPLEMENTATION_PROVIDER_URL", "").rstrip("/"),
            token=os.getenv("REIS_IMPLEMENTATION_PROVIDER_TOKEN", ""),
            required_capability="implementation_executor",
        )
    raise RuntimeError("UNKNOWN_PROVIDER_KIND")


def _founder_approval_ref() -> str:
    return os.getenv("REIS_ARTIFICIAL_BRAIN_FOUNDER_APPROVAL_REF", "")


def _authorize_caller(caller_token: str | None) -> None:
    expected = os.getenv("REIS_EXECUTION_BINDINGS_CALLER_TOKEN", "")
    if not expected:
        raise HTTPException(status_code=503, detail="CALLER_AUTH_BINDING_REQUIRED")
    if not caller_token or not secrets.compare_digest(caller_token, expected):
        raise HTTPException(status_code=401, detail="CALLER_AUTHENTICATION_REQUIRED")


def validate_envelope(envelope: ExecutionEnvelope) -> None:
    if envelope.program_id != PROGRAM_ID:
        raise HTTPException(status_code=403, detail="PROGRAM_SCOPE_MISMATCH")
    if envelope.gate not in AUTONOMOUS_GATES:
        raise HTTPException(status_code=403, detail="GATE_OUTSIDE_AUTONOMOUS_SCOPE")
    if envelope.capability in FORBIDDEN_CAPABILITIES:
        raise HTTPException(status_code=403, detail="FOUNDER_RESERVED_CAPABILITY")
    expected_approval = _founder_approval_ref()
    if not expected_approval:
        raise HTTPException(status_code=503, detail="FOUNDER_APPROVAL_BINDING_REQUIRED")
    if envelope.founder_approval_ref != expected_approval:
        raise HTTPException(status_code=403, detail="FOUNDER_APPROVAL_MISMATCH")


def _request_json(url: str, *, token: str = "", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    headers = {"Accept": "application/json"}
    method = "GET"
    data = None
    if payload is not None:
        method = "POST"
        data = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, method=method, headers=headers, data=data)
    try:
        with urlopen(request, timeout=5) as response:  # noqa: S310 - governed URL from deployment config
            if response.status < 200 or response.status >= 300:
                raise RuntimeError(f"HTTP_{response.status}")
            raw = response.read()
    except HTTPError as exc:
        raise RuntimeError(f"HTTP_{exc.code}") from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError("PROVIDER_UNAVAILABLE") from exc
    body = json.loads(raw.decode("utf-8"))
    if not isinstance(body, dict):
        raise RuntimeError("INVALID_PROVIDER_RESPONSE")
    return body


async def _probe(kind: str) -> tuple[bool, str]:
    config = _provider_config(kind)
    if not config.url:
        return False, f"{kind.upper()}_PROVIDER_URL_NOT_BOUND"
    try:
        body = await asyncio.to_thread(_request_json, f"{config.url}/health", token=config.token)
    except (RuntimeError, json.JSONDecodeError) as exc:
        return False, f"{kind.upper()}_PROVIDER_UNAVAILABLE:{exc}"
    if body.get("status") != "ok" or body.get(config.required_capability) is not True:
        return False, f"{kind.upper()}_PROVIDER_CONTRACT_NOT_SATISFIED"
    return True, f"{kind.upper()}_PROVIDER_READY"


async def _dispatch(kind: str, envelope: ExecutionEnvelope) -> dict[str, Any]:
    validate_envelope(envelope)
    config = _provider_config(kind)
    ok, detail = await _probe(kind)
    if not ok:
        raise HTTPException(status_code=503, detail=detail)
    payload = envelope.model_dump(mode="json")
    try:
        result = await asyncio.to_thread(
            _request_json,
            f"{config.url}/execute",
            token=config.token,
            payload=payload,
        )
    except (RuntimeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=503, detail=f"{kind.upper()}_EXECUTION_FAILED:{exc}") from exc
    return {
        "status": "accepted",
        "provider_kind": kind,
        "program_id": PROGRAM_ID,
        "gate": envelope.gate,
        "provider_result": result,
    }


@router.get("/health")
async def health() -> dict[str, Any]:
    authority, implementation = await asyncio.gather(_probe("authority"), _probe("implementation"))
    authority_ok, authority_detail = authority
    implementation_ok, implementation_detail = implementation
    return {
        "status": "ok",
        "program_id": PROGRAM_ID,
        "governed_effect_execution": authority_ok,
        "implementation_executor": implementation_ok,
        "founder_approval_bound": bool(_founder_approval_ref()),
        "authority_detail": authority_detail,
        "implementation_detail": implementation_detail,
        "autonomous_scope": [f"AB{i}" for i in range(6, 13)],
        "founder_reserved_gate": "AB13",
    }


@router.post("/effects/execute")
async def execute_effect(
    envelope: ExecutionEnvelope,
    x_reis_execution_token: str | None = Header(default=None),
) -> dict[str, Any]:
    _authorize_caller(x_reis_execution_token)
    return await _dispatch("authority", envelope)


@router.post("/implementation/execute")
async def execute_implementation(
    envelope: ExecutionEnvelope,
    x_reis_execution_token: str | None = None,
) -> dict[str, Any]:
    _authorize_caller(x_reis_execution_token)
    return await _dispatch("implementation", envelope)
