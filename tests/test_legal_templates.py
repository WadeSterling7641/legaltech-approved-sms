from __future__ import annotations

from typing import Any, Mapping

from legal_sms import LegalSmsService, MatterSmsRequest, SmsMoment
from legal_sms.legal_templates import choose_template


class RecordingRegistry:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Mapping[str, Any], str]] = []

    def create_signature(
        self, payload: Mapping[str, Any], *, idempotency_key: str
    ) -> Mapping[str, object]:
        self.calls.append(("signature", payload, idempotency_key))
        return {"signature_id": "sig_test"}

    def create_template(
        self, payload: Mapping[str, Any], *, idempotency_key: str
    ) -> Mapping[str, object]:
        self.calls.append(("template", payload, idempotency_key))
        return {"template_id": "tpl_test"}


def test_signed_document_event_selects_portal_delivery_wording() -> None:
    decision = choose_template(
        MatterSmsRequest("MAT-1042", "Avery Chen", SmsMoment.SIGNED_DOCUMENT)
    )

    assert decision.slug == "signed-document"
    assert "signed document" in decision.body
    assert "secure client portal" in decision.body
    assert decision.variables == ("client_name", "matter_reference")


def test_registration_uses_namespaced_assets_and_stable_write_keys() -> None:
    registry = RecordingRegistry()
    service = LegalSmsService(registry)

    result = service.register_approved_assets(
        MatterSmsRequest("MAT-1042", "Avery Chen", SmsMoment.DEADLINE_FOLLOW_UP),
        namespace="Demo Run 42",
        signature_name="Northstar Legal",
        proof_url="https://example.com/legal/sms-proof",
    )

    assert result.template_name == "legaltech-demo-run-42-deadline-follow-up"
    assert registry.calls[0][0] == "signature"
    assert registry.calls[0][2] == "legal-sms:demo-run-42:signature"
    assert registry.calls[1][1]["message_type"] == "transactional"
    assert registry.calls[1][2] == "legal-sms:demo-run-42:deadline-follow-up"
