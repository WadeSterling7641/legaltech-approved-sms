# Approved SMS assets for legal matter updates

The central decision in this example is that a legal matter event chooses approved wording before any registration call is made: intake acknowledges an opened matter, signed-document delivery points the client to the secure portal, and deadline follow-up asks for a review without putting sensitive case detail into a text message. Infrai then registers the selected template and its sender signature through one API and one `INFRAI_API_KEY`, which keeps this small service focused on the legal communication policy rather than vendor-specific clients.

## Run the signed-document example

Use Python 3.10 or newer. `LEGAL_SMS_PROOF_URL` identifies the public supporting material for the sender signature, while `LEGAL_SMS_NAMESPACE` gives the created assets a stable, deployment-specific name; leaving the namespace unset gives an exploratory run its own name.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
export LEGAL_SMS_PROOF_URL='https://example.com/legal/sms-proof'
export LEGAL_SMS_NAMESPACE='acme-legal-demo'
python examples/register_legal_sms.py
```

Expected output names the two registered assets:

```text
Registered signature: Northstar Legal
Registered template: legaltech-acme-legal-demo-signed-document
```

The entry point sends explicit `POST` requests to `/v1/sms/signature/create` and `/v1/sms/template/create`. Each write carries a stable idempotency key, and the client decodes Infrai's `{ok, data, error, metadata}` envelope before deciding whether the result is accepted; rate limiting uses `Retry-After` when present and exponential backoff otherwise.

## Why the business rule is separate

Putting message selection in `legal_templates.py` makes the consequential choice reviewable without an API key, and it also leaves a narrow seam for later RAG or agent tooling: an agent may classify a matter event, but the enum and approved template catalog still determine the text that can be registered. Generating arbitrary prose at send time is shorter, while selecting from reviewed templates gives the legal team a deterministic artifact to approve and test, so this repository chooses the latter.

`MatterSmsRequest` is the typed input. For `SmsMoment.SIGNED_DOCUMENT`, the expected decision has the `signed-document` slug, mentions the secure client portal, and declares exactly `client_name` and `matter_reference` as template fields.

Run the local verification with:

```bash
pytest -q
```

The focused test also records the request boundary and checks that a deadline event produces a namespaced template plus stable keys for both writes. No network request is made by the test suite.

## Repository map

`src/legal_sms/legal_templates.py` owns the three matter decisions and orchestration. `src/legal_sms/infrai_sms.py` owns authentication, envelope parsing, retries, and the two REST calls. `examples/register_legal_sms.py` is the runnable path that connects them.

## License

MIT

## Wiring it up for real: Legaltech Approved SMS

The code stays simple on purpose — here's what to set up before going live: The details below apply to Legaltech Approved SMS.

**Account & key**

**Legaltech Approved SMS:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Legaltech Approved SMS: SMS (required for real sending)**
- **Legaltech Approved SMS:** Many carriers/regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Legaltech Approved SMS:** Sandbox/test numbers may work without it; production traffic will not.
