# ApplyPilot

A free, local Windows job application assistant. Your profile, documents, browser sessions and application history stay on your computer. No hosted server or paid AI API is required.

**Status: 0.1 preview.** This is working software with automated core/browser tests, not a universal job-portal robot. See the feature table before using it.

## Download and install

1. Open [Releases](https://github.com/Sunnyvulli/auto-job-applier/releases/latest).
2. Download **ApplyPilot-Setup.exe** when a successful Windows build is available.
3. Run the installer. It bundles Python, required packages and Chromium; you do not install Python or Node yourself.
4. Open ApplyPilot, enter your verified profile, add jobs and click **Start selected**.

The unsigned installer can produce a Windows reputation warning. Verify that you downloaded it from this repository. No commercial signing certificate is included. Internet is needed to import jobs, open portals or sync mail, but no dependency downloads are needed after installing the built installer.

If Releases has no installer, the Windows build is not complete or failed. Check [Actions](https://github.com/Sunnyvulli/auto-job-applier/actions). Source code alone is not an executable.

## What actually works

| Feature | This release |
|---|---|
| Profile and reusable exact answers | Local editor and JSON import |
| Job imports | Greenhouse and Lever public company boards, including Lever EU |
| Job filtering | Company/title/location text filter, skill keyword overlap |
| Eligibility | User checks; overlap is not a sponsorship or eligibility decision |
| Resume and cover letter | PDF and text templates built only from profile facts, skill ordering based on job description |
| Browser autofill | Exact labeled fields, native selects and recognized document uploads; visible Chromium |
| Automatic submission | Optional on recognized Greenhouse/Lever hosts when required controls are resolved and a unique submit button is found |
| Other portals | Manual URL entry, best-effort exact autofill, human completion |
| Account creation/login | Complete in persistent browser; no automatic signup/password generation |
| CAPTCHA / device / SMS / authenticator | Human handoff in the same browser; no bypass or external paid solver |
| Email OTP | Enter manually in the browser; automatic extraction not implemented |
| Submission evidence | Local receipt JSON with URL, time and page text; positive confirmation required |
| Duplicate handling | Unique URL, atomic claims, no automatic retry of submitted/uncertain applications |
| Email tracking | Read-only IMAP using provider app password, or .eml file import |
| Email updates | Advisory interview/rejection/confirmation classification, dashboard alerts during session |
| Follow-up | Editable template and explicit Send; no unattended replies |
| Exports | CSV with spreadsheet formula protection |
| Scheduled discovery | Not implemented; start imports and queues from the app |
| LLM writing | Not included; no model download, API bill or fabricated achievements |

## First use

**Profile:** enter factual text for education, work and projects. Skills are comma-separated. Exact screening answers are a JSON object, for example `{"Do you need visa sponsorship?": "Yes"}`. Answers match the actual label exactly after whitespace/case normalization; unrelated questions remain unanswered. Do not put passwords in the profile.

**Jobs:** enter the company's board identifier (the company segment of its public Greenhouse/Lever board URL), choose provider/region, and import. Filter the results. Double-click a row to see its URL, description, status and notes. You can add an HTTPS application URL manually.

**Documents:** select a job and click Prepare PDFs. Review these before automatic submission. The generated resume includes only text you supplied. It does not read your existing PDF resume; paste verified content into Profile or import profile JSON.

**Applications:** select one or more jobs and click Start selected. Review mode is the default. Complete account creation, verification and custom controls in the visible browser. You may submit there yourself, then click Resume. Optional automatic submission attempts only recognized hosts and resolved forms. Complex portals will need you. Stop closes the session after the current browser operation returns.

**Receipts:** submitted means a positive confirmation phrase appeared on a changed page without visible editable fields. This conservative heuristic can miss valid submissions; check uncertain applications in the portal or email before resetting them. It cannot prove employer review or prevent duplicates across different URLs for the same opening.

**Email:** optional Gmail/Outlook IMAP requires IMAP enabled and an app password supported by your account. Passwords are stored through the operating-system keyring. Some accounts require OAuth and will not work with this release's IMAP login. Use .eml import instead. Sync reads the latest 100 messages without marking them read. Message-stage classification is advisory. Company matching only links a message when exactly one stored job matches; ambiguous messages remain unlinked. Follow-ups need an explicit recipient and Send confirmation.

## Data and security

On Windows data lives under `%LOCALAPPDATA%\ApplyPilot`. App binaries live separately under `%LOCALAPPDATA%\Programs\ApplyPilot`. Uninstalling the app leaves personal records for recovery; delete the data folder yourself if you want to erase them.

- No telemetry, hosted backend, public profile upload, web listener or required AI vendor.
- Email app password uses OS keyring, never SQLite. Normal account passwords are entered directly in the browser.
- Profile, email bodies, receipts and browser session files are sensitive local data, not encrypted database records. Protect your Windows account and disk. Never commit the data directory.
- Browser cookies can grant account access. Do not share the browser-session folder. Session persistence is not a password vault.
- Imported pages/email are treated as data, never AI instructions or executable commands. Native browser sandbox remains enabled.
- Work authorization, consent, demographic and sensitive questions are not guessed. Checkboxes/radios remain for the user.
- Submitted/uncertain jobs cannot be automatically retried. Restart converts interrupted running jobs to uncertain.
- The agent navigates user-chosen URLs in a browser. Inspect unfamiliar employers and destinations before supplying personal information.
- Automatic submission is opt-in. Clicking Start with it enabled authorizes submissions for the selected jobs. Email never sends automatically.

## Run from source

Requires Python 3.12 and a desktop display.

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
python launcher.py
```

Linux development also needs Tk and Chromium system dependencies. End users of the Windows installer do not need these steps.

## Test and build

```sh
pip install -r requirements.txt -r requirements-dev.txt
python -m playwright install chromium
python -m pytest -q
```

The GitHub workflow runs core/browser tests on Linux, then builds on Windows with PyInstaller and Inno Setup, silently installs and launches the resulting app, and publishes an installer only after those steps pass. CI fixtures use synthetic data; no real applications are submitted. Windows and live-employer validation must be reported separately from fixture tests.

The repository's workflow is intended for public GitHub-hosted standard runners. No paid services are configured. GitHub account policies/quotas can still prevent builds; no deployment or billing service is provisioned. GitHub Pages can host static pages, not this browser agent.

## Scope and roadmap

Next improvements: employer-specific adapters verified against live forms, OAuth email connection, robust DOM confirmation adapters, account creation workflows, optional local-model writing, notifications outside the running app, and scheduled imports. These are not claimed as completed capabilities.

A personal application assistant cannot guarantee access to every portal, CAPTCHA completion, submission success or employment. This release emphasizes visible progress and recoverable failures.

## Sources

- Greenhouse public Job Board API: https://docs.greenhouse.io/job-board
- Lever Postings API: https://github.com/lever/postings-api
- Playwright browser packaging: https://playwright.dev/python/docs/browsers
- PyInstaller Windows builds: https://pyinstaller.org/en/stable/

MIT licensed. Dependencies retain their respective licenses; Chromium licensing files are distributed with the browser bundle.
