"""Business decisions for approved legal matter SMS templates."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Protocol

from .infrai_sms import SignaturePayload, TemplatePayload


class SmsMoment(str, Enum):
    MATTER_INTAKE = "matter_intake"
    SIGNED_DOCUMENT = "signed_document"
    DEADLINE_FOLLOW_UP = "deadline_follow_up"


@dataclass(frozen=True)
class MatterSmsRequest:
    matter_reference: str
    client_name: str
    moment: SmsMoment


@dataclass(frozen=True)
class TemplateDecision:
    slug: str
    body: str
    variables: tuple[str, ...]
    message_type: str = "transactional"


@dataclass(frozen=True)
class RegistrationResult:
    signature_name: str
    template_name: str
    signature: Mapping[str, object]
    template: Mapping[str, object]


class SmsRegistry(Protocol):
    def create_signature(
        self, payload: SignaturePayload, *, idempotency_key: str
    ) -> Mapping[str, object]:
        raise AssertionError("protocol method called directly")

    def create_template(
        self, payload: TemplatePayload, *, idempotency_key: str
    ) -> Mapping[str, object]:
        raise AssertionError("protocol method called directly")


DECISIONS = {
    SmsMoment.MATTER_INTAKE: TemplateDecision(
        slug="matter-intake",
        body=(
            "Hello {{client_name}}, intake for matter {{matter_reference}} is open. "
            "Reply to your legal team if any submitted detail changes."
        ),
        variables=("client_name", "matter_reference"),
    ),
    SmsMoment.SIGNED_DOCUMENT: TemplateDecision(
        slug="signed-document",
        body=(
            "Hello {{client_name}}, the signed document for matter "
            "{{matter_reference}} is ready in your secure client portal."
        ),
        variables=("client_name", "matter_reference"),
    ),
    SmsMoment.DEADLINE_FOLLOW_UP: TemplateDecision(
        slug="deadline-follow-up",
        body=(
            "Hello {{client_name}}, a deadline for matter {{matter_reference}} "
            "needs your follow-up. Please review the client portal."
        ),
        variables=("client_name", "matter_reference"),
    ),
}


def choose_template(request: MatterSmsRequest) -> TemplateDecision:
    """Select approved wording from the observable matter event."""
    return DECISIONS[request.moment]


class LegalSmsService:
    def __init__(self, registry: SmsRegistry) -> None:
        self._registry = registry

    def register_approved_assets(
        self,
        request: MatterSmsRequest,
        *,
        namespace: str,
        signature_name: str,
        proof_url: str,
    ) -> RegistrationResult:
        decision = choose_template(request)
        safe_namespace = self._safe_namespace(namespace)
        template_name = f"legaltech-{safe_namespace}-{decision.slug}"

        signature_payload: SignaturePayload = {
            "name": signature_name,
            "type": "company",
            "proof_url": proof_url,
            "remark": "Approved legal matter client communications",
        }
        signature = self._registry.create_signature(
            signature_payload,
            idempotency_key=f"legal-sms:{safe_namespace}:signature",
        )

        template_payload: TemplatePayload = {
            "name": template_name,
            "body": decision.body,
            "locale": "en-US",
            "variables": list(decision.variables),
            "message_type": decision.message_type,
        }
        template = self._registry.create_template(
            template_payload,
            idempotency_key=f"legal-sms:{safe_namespace}:{decision.slug}",
        )
        return RegistrationResult(
            signature_name=signature_name,
            template_name=template_name,
            signature=signature,
            template=template,
        )

    @staticmethod
    def _safe_namespace(value: str) -> str:
        normalized = re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")
        if not normalized:
            raise ValueError("namespace must contain a letter or number")
        return normalized
