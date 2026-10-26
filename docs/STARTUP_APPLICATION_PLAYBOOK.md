# Startup application workflow

This playbook converts observed application problems into repeatable operating
steps and regression tests. It is not model-weight training and does not promise
universal portal support or employer acceptance.

## Dependencies and execution environments

The Windows application uses Python, Playwright with its installed Chromium,
ReportLab for PDFs, pypdf for reading documents, keyring for local credentials,
and google-auth-oauthlib for consented Gmail access. Exact versions are in
`../requirements.txt`. Development checks use `../requirements-dev.txt`.
The hosted assistant's browser and Gmail connectors are separate tools; installing
ApplyPilot does not provide those services, their sessions or permissions.

## Applicant inputs (private local configuration)

Use Profile for name, explicit first/last names, contact details and links.
Use reviewed facts and source resumes for education, skills and employment.
Keep resume PDFs, answer declarations, receipts and consent evidence locally;
never commit actual applicant contact data, immigration records, credentials,
browser cookies or CAPTCHA responses. Example fixtures use synthetic values.
Keep separate dated answers for current work authorization and future sponsorship.
A current F-1 declaration alone does not establish employer-specific CPT approval.
Do not infer either answer from earlier employers or learn it as a generic answer.

## Before each application

1. Verify the company's product, identity and opening using its official careers
   page or a recruiting page linked by that company. Reject applicant fees,
   deposits, profile marketing and paid-placement/training intermediaries.
2. Read the entire role. Short listing labels such as “new grads welcome” may
   conflict with a detailed requirement for several years of production experience.
3. Map each material requirement to dated resume/project evidence. Count unknown
   requirements as unsupported. Apply only at 70% or greater supported coverage,
   with all mandatory location, experience and eligibility requirements satisfied.
   Record the denominator and evidence; do not treat keyword similarity as proof.
4. Check history and Gmail receipts for the company AND role ID. Preserve
   user-reported submissions separately from receipt-confirmed submissions.
5. Prepare PDFs, review the actual generated document, and tailor the note to
   the company's problem. Project work remains labelled project work. Do not add
   tools, employment, dates, publications or production claims without evidence.

## Form execution and recovery

- Open the real application in the same browser tab, then Resume browser.
- Fill identity from the reviewed profile. City search text is not a selected
  location: select the exact city/state/country option and verify it remains set.
- Select authorization answers only from explicit reviewed declarations. A
  combined “now or in future” question needs an answer covering both periods.
- Upload the prepared resume through the file chooser and verify the displayed
  filename. In the hosted browser, the documented shared-directory mapping is
  required; a Windows desktop installation instead uses its own local file path.
- CAPTCHA and login verification require human intervention. CAPTCHA completion
  may expire while other fields are prepared. Preserve the filled form and ask
  for the check again; do not bypass or store its token.
- Respect destination-specific permission and any binding agreement confirmation.
  One employer's approval does not imply consent for unrelated data disclosures.
- A blocked form should not end a batch: record it and proceed with other verified
  roles when possible. Batch targets do not relax evidence or eligibility checks.
- After Submit, verify a matching success state or receipt. No visible receipt
  means uncertain; never blindly retry. A user saying “Submitted” is recorded as
  user-reported, and suppresses duplicates pending receipt verification.

## Lessons from the observed Tank Payments flow

The YC company job route exposed an application dialog with contact fields,
location autocomplete, separate work-authorization and combined sponsorship
radios, a resume chooser, tailored-interest text and hCaptcha. The user completed
the CAPTCHA; it later expired. Contact fields and a PDF were filled after
destination-specific approval. The user subsequently reported submission.
No assistant-observed success state was captured, so this is a user-reported
submission, not evidence of a fully autonomous successful live application.

Shared YC URLs now scope correction memories to the employer slug in the observed
route. Unscoped application URLs return no reusable employer scope. Work-eligibility
and sponsorship fields are excluded from correction memory, including old memories
at lookup time. Existing matching already checks role, location, field type,
choices, profile hash and expiry. These rules prevent unsafe cross-context reuse.

## Verification and future learning

Run `python -m pytest tests/test_startup_learning.py tests/test_learning.py`.
For each new failure, create an anonymized form fixture, document expected and
actual behavior, fix the supported adapter and add a regression before claiming
support. Never promote an unconfirmed action to a success example. Fixture tests
show code behavior; they do not prove delivery, hiring outcomes, live ATS support
or an installed Windows upgrade. The 20–30 application batch target belongs to
the operating workflow; it is not a newly implemented desktop scheduler.

## Direct-employer scope and access triage

The operating search includes established direct employers as well as startups.
Prioritize portals without human verification. A visible application dialog is
not proof that a CAPTCHA will not appear on submission. Inspect the current
form before choosing a route; do not classify a plain login or timeout as a bot
block. Skip verification-dependent forms and continue the batch without solving
or bypassing their checks. Preserve the exact blocker and application state.

For hosted browser runs, destination-specific permission to share private
contact information and a resume may be required before filling, even when the
form itself has no CAPTCHA. Record `awaiting_destination_permission` separately
from `captcha_required`, `authentication_required` and `submitted_confirmed`.
An unattended run cannot turn a pending permission into approval. Never use a
different transport to evade an approval requirement.

Observed public new-graduate YC flow: Apply opens an in-page dialog containing
identity/contact fields, location autocomplete, two separate authorization
questions, resume upload and a message. No challenge was visible at initial
inspection. No submission was made, so this is a discovery example only. Do not
label it as a successful adapter or train success counters from it.
