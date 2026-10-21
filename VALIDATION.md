# Validation record

## Local verification

- 27 automated checks passed on Linux/Python 3.12.
- Chromium tests exercised real DOM filling, exact selects, sensitive consent handoff and correct file upload selection.
- A full browser-worker queue test intercepted a synthetic Lever URL, filled and submitted a synthetic form, detected its confirmation, saved a receipt and prevented a second claim.
- Core tests cover duplicate URLs, atomic claims, submitted-record protection, interruption recovery, profile-derived PDFs, invalid URL rejection, exact answers, board import mappings, mail deduplication and ambiguous email matching.
- Process instance lock tested for exclusion and re-acquisition.
- Python compilation check passed.

## Separate checks

Windows installer building, installation and GUI startup run in GitHub Actions. Their authoritative result is the linked Actions run and published installer, not these local results. Linux GUI startup could not be checked in the local environment because it has no display server.

## Not verified

No live employer application was submitted. No real email inbox was connected. No portal account was created. No CAPTCHA was solved. Cross-portal compatibility and positive-confirmation heuristics are not guaranteed by the fixture tests.

## Read-only live import check

On 2026-10-21, the adapter parsed 897 Databricks listings through Greenhouse and 304 Palantir listings through Lever with valid title/URL fields. These are source-adapter checks, not eligibility endorsements. Supabase returned 404 for the tested Greenhouse board identifier, which was handled as an import error. No applications were sent.

## 0.2 development

- Added Ashby and paginated SmartRecruiters feeds, board URL validation, selected-job detail hydration and recurring saved-source refresh.
- Added exact-origin credential-vault helpers, scoped email-code extraction/filling, Gmail Desktop OAuth integration, HTML mail parsing and optional recurring mail sync.
- Browser fixtures cover multi-step advancement, hidden file uploads, required custom dropdown handoff, credential-origin isolation, third-party frame exclusion and explicit OTP targeting.
- Local tests exercise stale/wrong-sender/wrong-recipient/ambiguous code rejection, OAuth client endpoint checks, source pagination, password absence from SQLite and deterministic connection closure.
- Read-only live check: Ashby Ramp returned 170 valid listings; the Notion board returned HTTP 403 in this environment. Empty responses for other tested company identifiers are treated as zero results, not claimed as coverage of those companies.
- Windows workflow additionally checks packaged OAuth imports and a temporary synthetic credential round trip in the Windows vault. Its result must pass before publication.
- Real employer application submission, real signup, live user Gmail OAuth consent and real inbox credentials are still not validated by fixtures.

0.2 local result: **50 tests passed** on Linux/Python 3.12. Read-only SmartRecruiters BoschGroup import completed with 5,099 valid listings (the live count changed from the initial API preflight). Ashby Ramp returned 170. No application or account registration was submitted.
