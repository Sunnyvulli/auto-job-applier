# Validation record

## Local verification

- 26 automated checks passed on Linux/Python 3.12.
- Chromium tests exercised real DOM filling, exact selects, sensitive consent handoff and correct file upload selection.
- A full browser-worker queue test intercepted a synthetic Lever URL, filled and submitted a synthetic form, detected its confirmation, saved a receipt and prevented a second claim.
- Core tests cover duplicate URLs, atomic claims, submitted-record protection, interruption recovery, profile-derived PDFs, invalid URL rejection, exact answers, board import mappings, mail deduplication and ambiguous email matching.
- Process instance lock tested for exclusion and re-acquisition.
- Python compilation check passed.

## Separate checks

Windows installer building, installation and GUI startup run in GitHub Actions. Their authoritative result is the linked Actions run and published installer, not these local results. Linux GUI startup could not be checked in the local environment because it has no display server.

## Not verified

No live employer application was submitted. No real email inbox was connected. No portal account was created. No CAPTCHA was solved. Cross-portal compatibility and positive-confirmation heuristics are not guaranteed by the fixture tests.
