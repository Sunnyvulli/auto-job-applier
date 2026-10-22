# Validation record

## 0.1 local verification

- 27 automated checks passed on Linux/Python 3.12.
- Chromium tests exercised real DOM filling, exact selects, sensitive consent handoff and correct file upload selection.
- A full browser-worker queue test intercepted a synthetic Lever URL, filled and submitted a synthetic form, detected its confirmation, saved a receipt and prevented a second claim.
- Core tests cover duplicate URLs, atomic claims, submitted-record protection, interruption recovery, profile-derived PDFs, invalid URL rejection, exact answers, board import mappings, mail deduplication and ambiguous email matching.
- Process instance lock tested for exclusion and re-acquisition.
- Python compilation check passed.

## 0.1 separate checks

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

0.2 local result: **51 tests passed** on Linux/Python 3.12. Read-only SmartRecruiters BoschGroup import completed with 5,099 valid listings (the live count changed from the initial API preflight). Ashby Ramp returned 170. No application or account registration was submitted.

## 0.3 development

- Replaced full-table redraws with indexed pagination, debounce and incremental rows; added bulk transactions, WAL, batched candidate scans, bounded parallel source imports and HTTP session pooling.
- Added native dashboard/navigation, light/dark styling, screen-size adjustment, scrollable pages, preference queues, PDF/DOCX/text resume import, original-PDF preservation, a reusable-answer editor and verified document caching.
- Local result: 59 core/browser/productivity tests passed; one desktop test was skipped without a display, then passed separately under a virtual display (60 distinct passing checks across both runs).
- Desktop interaction test exercises profile/answers/preferences, source add/remove/deduplication, pagination, low resource pages, all views at 1240×820 / 1024×700 / 960×640 and theme switching. Development screenshots used synthetic data and were visually inspected; these are not Windows hardware screenshots.
- Synthetic benchmark: 10,000-job bulk insert 0.1945 s; 100-row page median 0.634 ms; queue scan 0.0989 s. The 1,000-record bulk path was 69.65× faster than individual transactions in this Linux container. These figures do not predict network speed, portal completion or physical laptop performance.
- Installer pipeline builds Full and Lite, tests both on Windows Server 2022 and 2025, and separately attempts Windows 11 ARM emulation. Exact job results remain authoritative; ARM is experimental and may fail without blocking x64 publication.
- Live employer submissions, unattended account registration, real user OAuth consent, CAPTCHA completion and legacy Windows compatibility remain unvalidated.


## 0.4 review and regression checks

Review identified third-party-frame profile filling and stale profile-derived documents between queued jobs. The fixes restrict frame filling to the page origin, refresh profile data per job and rebuild cached documents after a profile/original-resume change during a pause. Missing selected original PDFs now stop preparation. Saved queues are rechecked against current preferences/status; heap ranking bounds candidate memory to the queue cap.

Recovery tests cover data/history restoration, preservation of submitted-job protection, portable original resumes, conservative interrupted statuses, excluded vault/browser credentials, safety copies, archived old receipts, transaction/folder rollback on a simulated database failure, corrupt hashes, oversized input, unexpected/duplicate ZIP paths, invalid job IDs/statuses/settings and five-date rotation. Packaged Windows checks now also exercise backup export and restore. New desktop checks exercise queue preflight and removal.

Exact CI results and release assets remain authoritative. Fixture tests still do not validate real employer submissions, real account registrations, live Gmail consent or universal portal compatibility.

The first 0.4 Windows run exposed a desktop-test lifecycle issue: a second Tcl/Tk interpreter could not initialize its theme files after the first was destroyed. GUI tests now share one interpreter across separate windows and cancel scheduled callbacks on teardown, matching the single-instance application design. Windows installation checks still run in fresh application processes.


## 0.5 job-specific drafts

Added local resume/cover-letter proposals, a verified fact bank, exact per-job custom-answer approvals, evidence/gap display and editable diffs. No remote model service or paid dependency was added. Tests cover supported-fact selection, preservation of employment/education, no insertion of missing technologies, approval gates, per-job isolation, sensitive-question handoff, country and total-versus-specific experience boundaries, source/profile/job/fact invalidation, optimistic revision conflicts, backup portability with disabled approvals, legacy backup compatibility and PDF output. Browser fixtures check approval before filling and explicit handling of field length limits. A desktop test exercises the draft editor, fact bank, resume approval, answer approval/revocation and stale-context rejection. Packaged-app checks additionally generate reviewed job-specific documents before backup/restore. Exact CI outcomes remain authoritative.


## 0.6 learned corrections

Added local scoped answer memory, a confirmation gate, review/disable/delete/global-copy controls and support for native labeled radio groups. Browser integration tests run two synthetic applications sequentially: the first pauses for a manual correction, detects submission confirmation and activates memory; the second fills and submits without that pause. This is checked for numeric text, native select and native radio fields. Core tests cover employer/role/location isolation, pending-versus-active reuse, profile/fact invalidation, forbidden fields, native-invalid/unchanged values, changed choices, explicit per-job approval precedence, expiry, correction replacement, disabling/forgetting, and restored-disabled memory. Desktop tests exercise memory review and global promotion; packaged checks exercise learning and its review window. No real employer submissions or general portal-workflow learning are established by these fixtures.
