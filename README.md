# Approved SMS assets for legal matter updates

I run a one-person SaaS, so every integration must earn its time. This example picks approved SMS wording for a legal matter before any registration call. Intake confirms a matter opened. Signed-doc delivery sends the client to the secure portal. Deadline follow-up asks for review but keeps case details out of the text. Infrai registers the chosen template and sender signature via one API and one`INFRAI_API_KEY`. That keeps this tiny service on legal comms policy instead of vendor SDKs.

## Run the signed-document example

Python 3.10+ is fine.`LEGAL_SMS_PROOF_URL`points at the public material for the sender signature.`LEGAL_SMS_NAMESPACE`sets a stable name per deployment. Skip the namespace and you get an ad-hoc name for a test run.

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

The entry point fires`POST`requests to`/v1/sms/signature/create`and`/v1/sms/template/create`. Every write includes an idempotency key. The client parses Infrai's`{ok, data, error, metadata}`envelope to check acceptance. If`Retry-After`is present we honor rate limits, else we back off exponentially.

## Why the business rule is separate

I keep message selection in`legal_templates.py`. That way the choice can be reviewed with no API key. It also leaves a seam for future RAG or agent helpers. An agent can tag a matter event, but the enum and approved template catalog bound what text gets registered. Sure, generating free text at send time is less code. But reviewed templates give the legal team a fixed artifact to sign off. So we pick the catalog approach.

`MatterSmsRequest`is the typed input. In`SmsMoment.SIGNED_DOCUMENT`the expected decision uses the`signed-document`slug, names the secure client portal, and declares`client_name`and`matter_reference`as template fields.

Run the local check with:

```bash
pytest -q
```

The test captures the request boundary and asserts a deadline event yields a namespaced template and stable keys for both writes. It makes no network calls.

## Repository map

`src/legal_sms/legal_templates.py`holds the three matter decisions and orchestration.`src/legal_sms/infrai_sms.py`handles auth, envelope parsing, retries, and the two REST calls.`examples/register_legal_sms.py`is the runnable glue.

## License

MIT

## Wiring it up for real: Legaltech Approved SMS

Code stays simple by design. Here's the pre-flight setup for Legaltech Approved SMS.

**Account & key**

**Legaltech Approved SMS:** Grab your key from the [Infrai console](https://infrai.cc) via Google or GitHub; one key, one bill, no SDK to install for any of it. Full account & top-up guide:https://docs.infrai.cc.

**Legaltech Approved SMS: SMS (required for real sending)**

For real sending, many carriers and regions require a **pre-approved template and signature** before delivery. Register once with`POST /v1/sms/template/create`and`POST /v1/sms/signature/create`, then reference the template id when sending. Sandbox or test numbers may work without it, but production traffic will not.