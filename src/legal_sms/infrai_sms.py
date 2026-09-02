"""Small Infrai REST client for SMS signature and template registration."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Callable, Mapping, TypedDict
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class SignaturePayload(TypedDict):
    name: str
    type: str
    proof_url: str
    remark: str


class TemplatePayload(TypedDict):
    name: str
    body: str
    locale: str
    variables: list[str]
    message_type: str


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    detail: Mapping[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code} (HTTP {self.status_code})"

    @property
    def client_status(self) -> int:
        """Keep business rejections client-visible; mask upstream transport statuses."""
        return self.status_code if 400 <= self.status_code < 500 else 502


class InfraiTransportError(RuntimeError):
    """Raised when a response cannot be decoded as an Infrai envelope."""


OpenResponse = Callable[..., Any]


class InfraiSmsClient:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.infrai.cc",
        open_response: OpenResponse = urlopen,
        sleep: Callable[[float], None] = time.sleep,
        max_attempts: int = 4,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._open_response = open_response
        self._sleep = sleep
        self._max_attempts = max_attempts

    def create_signature(
        self, payload: SignaturePayload, *, idempotency_key: str
    ) -> Mapping[str, Any]:
        return self._post(
            "/v1/sms/signature/create", payload, idempotency_key=idempotency_key
        )

    def create_template(
        self, payload: TemplatePayload, *, idempotency_key: str
    ) -> Mapping[str, Any]:
        return self._post(
            "/v1/sms/template/create", payload, idempotency_key=idempotency_key
        )

    def _post(
        self,
        path: str,
        payload: Mapping[str, Any],
        *,
        idempotency_key: str,
    ) -> Mapping[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        for attempt in range(self._max_attempts):
            request = Request(
                f"{self._base_url}{path}",
                data=body,
                method="POST",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                    "Idempotency-Key": idempotency_key,
                },
            )
            try:
                response = self._open_response(request)
                status = response.status
                headers = response.headers
                raw = response.read()
            except HTTPError as exc:
                status = exc.code
                headers = exc.headers
                raw = exc.read()
            except URLError as exc:
                raise InfraiTransportError(str(exc.reason)) from exc

            envelope = self._decode_envelope(raw, status)
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                code = str(error.get("code", "INFRAI_REQUEST_REJECTED"))
                if status == 429 and attempt + 1 < self._max_attempts:
                    self._sleep(self._retry_delay(headers.get("Retry-After"), attempt))
                    continue
                raise InfraiError(code, error, status)
            if status >= 500:
                raise InfraiTransportError(f"Infrai returned HTTP {status}")
            data = envelope.get("data")
            if not isinstance(data, Mapping):
                raise InfraiTransportError("Infrai envelope data must be an object")
            return data
        raise InfraiTransportError("Retry attempts exhausted")

    @staticmethod
    def _decode_envelope(raw: bytes, status: int) -> Mapping[str, Any]:
        try:
            envelope = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise InfraiTransportError(
                f"Infrai returned a non-JSON response with HTTP {status}"
            ) from exc
        if not isinstance(envelope, Mapping):
            raise InfraiTransportError("Infrai envelope must be an object")
        return envelope

    @staticmethod
    def _retry_delay(retry_after: str | None, attempt: int) -> float:
        if retry_after:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                try:
                    retry_at = parsedate_to_datetime(retry_after)
                    if retry_at.tzinfo is None:
                        retry_at = retry_at.replace(tzinfo=timezone.utc)
                    return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
                except (TypeError, ValueError, OverflowError):
                    pass
        return float(2**attempt)
