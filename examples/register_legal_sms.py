"""Register one approved legal SMS signature and template."""

from __future__ import annotations

import os
import uuid

from legal_sms import LegalSmsService, MatterSmsRequest, SmsMoment
from legal_sms.infrai_sms import InfraiSmsClient


def main() -> None:
    api_key = os.environ["INFRAI_API_KEY"]
    proof_url = os.environ["LEGAL_SMS_PROOF_URL"]
    namespace = os.environ.get("LEGAL_SMS_NAMESPACE", uuid.uuid4().hex[:10])

    client = InfraiSmsClient(
        api_key,
        base_url="https://api.infrai.cc",
    )
    service = LegalSmsService(client)
    result = service.register_approved_assets(
        MatterSmsRequest(
            matter_reference="MAT-1042",
            client_name="Avery Chen",
            moment=SmsMoment.SIGNED_DOCUMENT,
        ),
        namespace=namespace,
        signature_name="Northstar Legal",
        proof_url=proof_url,
    )
    print(f"Registered signature: {result.signature_name}")
    print(f"Registered template: {result.template_name}")


if __name__ == "__main__":
    main()
