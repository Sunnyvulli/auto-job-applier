# ApplyPilot 0.7 — automatic job discovery

## What changed

- Added **Discover jobs** with automatic search across 37 catalog employers plus saved sources.
- Added required country and optional city filters, per-source coverage/error reports and optional 15-minute discovery while open.
- Added **Find & apply**, which starts a bounded application queue restricted to the current search results.
- Preserved structured employer country data and excluded ambiguous free-text country/state abbreviations.
- Added a [step-by-step user guide](https://github.com/Sunnyvulli/auto-job-applier/blob/main/docs/USER_GUIDE.md), troubleshooting and upgrade instructions.

## How to use it

1. In **Preferences**, save roles such as `Data Engineer, Machine Learning Engineer` and countries such as `United States, India`.
2. Leave **Cities** blank unless you want a narrower search; review skill/seniority filters and queue size.
3. In **Discover jobs**, choose **Find jobs** to import and review, or **Find & apply** to search and start the assistant.
4. Automatic submission still uses the existing opt-in Overview setting and supported-form rules.

## Upgrade

Export a backup in **Diagnostics**, close ApplyPilot, install the latest Full/Lite edition and reopen. No new API key, paid service or separate Python installation is needed for discovery. Existing saved profiles/preferences/history normally remain in the data folder. Add the new country preference before using discovery. See the [upgrade instructions](https://github.com/Sunnyvulli/auto-job-applier/blob/main/docs/USER_GUIDE.md#9-upgrade-and-back-up).

## What was verified

For the discovery code released as build-15: **132 tests plus five desktop checks passed**. Both installer editions passed installed-app checks on Windows Server 2022/2025 and Windows 11 ARM emulation. A read-only live search scanned 16,570 listings from all 37 catalog feeds and imported 123 matches for Data Engineer/Machine Learning Engineer in US/India, with seniority exclusion off. A live optional-city check found UK/London engineer roles. Counts are observations, not promised results.

The subsequent guide/release-process change is documentation/workflow only; no application code or installed binary changed. Documentation links, control labels and workflow structure were reviewed. It does not constitute a new Windows installation test.

## Remaining limits

Coverage is a finite catalog plus saved sources, not every company or portal. Country-unknown listings are excluded. Automatic submission is opt-in for recognized Lever/Greenhouse forms; other forms and verification can need help. No CAPTCHA bypass is included. Real employer submissions, account creation and the user's live inbox remain unvalidated. Windows 11 ARM remains experimental.

Future releases attach the user guide and these release notes alongside installers. Version history is in [CHANGELOG.md](https://github.com/Sunnyvulli/auto-job-applier/blob/main/CHANGELOG.md).
