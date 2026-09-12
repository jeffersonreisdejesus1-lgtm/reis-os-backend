from __future__ import annotations

import json
from dataclasses import asdict
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .contracts import DispatchRequest, HostExecutionReceipt, OCSBinding


class HostAdapterError(RuntimeError):
    pass


class HttpHostAdapter:
    """Concrete fail-closed adapter for an authorized HTTP execution host.

    The remote host MUST echo the institutional binding fields in its receipt.
    This adapter does not infer or fabricate identity from provider/model names.
    """

    def __init__(self, *, endpoint: str, bearer_token: str | None = None, timeout_seconds: float = 30.0) -> None:
        if not endpoint.startswith(("https://", "http://")):
            raise ValueError("host_adapter_endpoint_invalid")
        self._endpoint = endpoint
        self._bearer_token = bearer_token
        self._timeout_seconds = timeout_seconds

    def invoke(
        self,
        request: DispatchRequest,
        target: OCSBinding,
        correlation_id: str,
    ) -> HostExecutionReceipt:
        body = {
            "mission_id": request.mission_id,
            "target": asdict(target),
            "invocation_kind": request.invocation_kind.value,
            "payload": request.payload,
            "correlation_id": correlation_id,
        }
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._bearer_token:
            headers["Authorization"] = f"Bearer {self._bearer_token}"

        wire_request = Request(
            self._endpoint,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(wire_request, timeout=self._timeout_seconds) as response:  # noqa: S310
                raw = response.read().decode("utf-8")
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise HostAdapterError("host_adapter_transport_failure") from exc

        try:
            payload = json.loads(raw)
            output = payload["output"]
            if not isinstance(output, dict):
                raise TypeError("output_must_be_object")
            return HostExecutionReceipt(
                mission_id=str(payload["mission_id"]),
                target_ocs_id=str(payload["target_ocs_id"]),
                target_instance_id=str(payload["target_instance_id"]),
                generation=int(payload["generation"]),
                host=str(payload["host"]),
                correlation_id=str(payload["correlation_id"]),
                output=output,
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise HostAdapterError("host_adapter_receipt_invalid") from exc
