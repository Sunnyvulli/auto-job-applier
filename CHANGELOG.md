# ApplyPilot version history

## 0.7.1 — autofill and resume-upload fixes

- Wait for delayed application controls before filling and matching saved answers.
- Read aria-labelledby labels, ordinary identity-field aliases and optional explicit name parts.
- Recognize hidden resume/cover-letter inputs labelled Attach using explicit input identity; hold ambiguous uploads for review.
- Continue filling contact fields after a missing/failed upload; report field/document-selection counts.
- Recognize supported manually selected React-select values on Resume while keeping custom choices manual.
- Extend packaged-app smoke checks to fill synthetic identity fields and select a hidden Attach resume input.
- Updated troubleshooting and upgrade guidance. No live employer submission is claimed.

## 0.7 — automatic discovery

- Discover jobs by roles/countries and optional cities across the employer catalog plus saved sources.
- Find & apply queues only current search results; submitted/uncertain jobs remain protected.
- Per-source reports, recurring import-only discovery, structured locations and conservative country matching.
- Added user guide, troubleshooting, upgrade instructions and a release-note workflow for future changes.
- Validation of discovery build-15: 132 tests plus five desktop checks; Full/Lite installed-app checks on Windows Server 2022/2025 and ARM emulation. Live read-only discovery: 16,570 listings, 123 matches in the recorded sample.

## 0.6 — correction learning

- Capture eligible manual corrections on Resume, with pending/confirmed reuse and scoped answer memory.
- Review, disable, forget or explicitly enable memories; support native labeled radio groups.
- Exclude verification, credentials, protected information and consent from learning.

## 0.5 — job-specific drafts

- Draft studio for reviewed resume/letter PDFs and exact job-specific custom answers.
- Saved fact bank, evidence/gap view and approval invalidation after relevant changes.

## 0.4 — recovery

- Logical backup export/restore, daily recovery copies and queue preflight checks.

Earlier preview work introduced source feeds, the desktop dashboard, document generation, browser assistance, email integration and Windows Full/Lite packaging. See Git history and individual releases for details.
