# ApplyPilot 0.2

Free local Windows job application assistant. No server subscription, paid AI API or CAPTCHA-solving service is configured. Profile, documents and application history remain on your computer.

**Preview software:** the feature coverage below is explicit. Real employer submissions and real account registrations have not been performed by the developer.

## Install

Download **ApplyPilot-Setup.exe** from [Releases](https://github.com/Sunnyvulli/auto-job-applier/releases/latest) after a successful build. Run it, save your profile, import company jobs, select suitable roles and click **Start selected**. The installer bundles Python, required packages and Chromium. No Python/Node installation is required. Internet is required for portals and mail. The installer is unsigned and Windows may show a reputation warning.

An existing installation can be upgraded using the same installer. Personal data remains under `%LOCALAPPDATA%\ApplyPilot`; binaries live under `%LOCALAPPDATA%\Programs\ApplyPilot`. Uninstall leaves personal records for recovery. Delete the data folder separately to erase them.

## Feature coverage

| Feature | Implemented behavior |
|---|---|
| Public job feeds | Greenhouse, Lever global/EU, Ashby and SmartRecruiters |
| Board input | Company identifier or recognized board URL |
| SmartRecruiters | Paginated listings; full description fetched when preparing a selected job |
| Saved sources | Refresh multiple company boards; optional refresh every 15 minutes while the app is open |
| Job selection | Title/location/company filter and skill keyword overlap; user checks eligibility/sponsorship |
| Documents | Profile-derived PDF/text resume and cover letter; matched skills listed first |
| Browser forms | Exact labeled text fields, native selects, visible/hidden resume uploads and multi-step Next/Continue |
| Automatic submission | Opt-in on recognized Lever/Greenhouse hosts when required native controls are resolved |
| Ashby / SmartRecruiters applications | Import support plus assisted browser completion; dedicated unattended application adapters are not provided |
| Other portals | Manually add URL; exact autofill and human completion |
| Account setup | Generate or save a password in the OS vault; fill login/signup fields on an explicitly approved origin |
| Account registration | User reviews terms and submits registration in the browser; account creation is not independently automated |
| Email verification | Fetch and fill one unique, fresh six-digit code from an explicitly approved sender for the current origin |
| CAPTCHA / SMS / authenticator | User completes the challenge in the same browser and resumes; no bypass |
| Email tracking | Gmail OAuth, IMAP app password, or .eml import; optional five-minute sync while open |
| Follow-up | Editable draft and explicit Send confirmation; OAuth sending requires send permission |
| Submission history | Receipt JSON, timestamps, page text and conservative positive-confirmation detection |
| Duplicate protection | Unique job URL, atomic queue claims, interrupted-session recovery; submitted/uncertain jobs are not automatically retried |
| Export | CSV with spreadsheet formula protection |
| LLM / scheduled auto-apply | Not included; feed refresh never triggers applications |

## First use

1. **Profile:** enter only factual education, experience, projects and skills. Skills are comma-separated. Import profile JSON if preferred; `profile.example.json` shows the format. Existing PDF resume parsing is not implemented.
2. **Exact answers:** a JSON object maps actual question labels to verified answers, such as `{"Do you need sponsorship?": "Yes"}`. Similar questions are not treated as equivalent. Work authorization, consent, demographic answers and unknown qualifications are not guessed.
3. **Jobs:** choose a provider and company identifier/board URL. Imports do not apply for anything. Double-click a job to read its URL, description, status and notes. Keyword overlap is not proof of eligibility.
4. **Saved sources:** use one line per board: `Greenhouse | databricks | global`, `Lever | palantir | global`, `Ashby | ramp | global`, or your chosen SmartRecruiters identifier. Save before refreshing. Recurring imports stop when the app closes.
5. **Prepare PDFs:** review the generated documents before automatic submission. This version uses extractive templates, not an LLM.
6. **Start selected:** review mode is the default. Complete unknown controls and verification in Chromium, then Resume. The updated worker re-evaluates the current page after each manual step instead of immediately declaring the application finished.
7. **Uncertain:** check portal/email before resetting a job. A text/DOM confirmation heuristic can miss a valid submission. It does not prove employer review or deduplicate different URLs for the same opening.

## Accounts and verification

Select a job and open **Account tools**. Confirm the exact portal URL and your email, then generate a password for a new account or save an existing password. Passwords are stored by the OS keyring, not SQLite. While an application is paused, **Fill saved account** fills account email/password in the top frame on that exact HTTPS origin. It never fills third-party frames or submits registration automatically. Review the site and its terms yourself.

Some shared ATS hosts keep separate accounts for different employers. This release stores one account per origin; use browser entry directly if employer accounts differ. Do not replace a saved password unless intended.

For email codes, configure the exact verification sender in Account tools and connect your mailbox. On the portal's code screen, click **Fetch email code** while paused. The helper requires the configured sender, your recipient address, a fresh message after the queue began, explicit verification language and one unambiguous six-digit code. It fills only a supported OTP field and does not submit it. Split-digit widgets, links, stale/ambiguous codes and SMS/authenticator approvals use manual entry. Codes and passwords are never written to activity logs.

## Email

**Gmail OAuth:** see [Gmail setup](docs/GMAIL_SETUP.md). OAuth needs your own Google Desktop app client registration; no shared OAuth credentials are distributed. Import client JSON, connect in your normal browser and grant read access. Send permission is optional. Tokens/configuration are stored in the OS vault. The verified Gmail account address is saved automatically.

**IMAP:** select Gmail or Outlook, enter the address and save a provider-generated app password. The provider must support that login method. OAuth-only accounts can use Gmail OAuth or .eml import where applicable. Outlook OAuth is not implemented.

Sync reads recent inbox messages without marking them read. HTML-only messages are supported. Interview/rejection classification is advisory; ambiguous company matching stays unlinked. Optional five-minute sync runs only while the app is open and reports new possible interview/action messages in the dashboard. It does not send replies automatically.

## Development and checks

Python 3.12 and a desktop display are needed when running source. Windows installer users skip these commands.

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
python -m playwright install chromium
python -m pytest -q
python launcher.py
```

Linux development also needs Tk and Chromium system dependencies. [GitHub Actions](https://github.com/Sunnyvulli/auto-job-applier/actions) tests Linux/browser fixtures, builds a Windows installer, installs it, exercises the dashboard/PDF/bundled browser/OAuth imports/Windows credential vault, and publishes only after success. Superseded builds do not publish a release. See [validation](VALIDATION.md) and [security review](SECURITY.md).

The app runs on your PC. GitHub hosts source and installer downloads; GitHub Pages cannot run this browser agent. Builds use standard public hosted runners and remain subject to GitHub account policies/availability. No paid infrastructure is provisioned.

MIT licensed. Dependencies retain their respective licenses. Chromium license files are bundled with its distribution.
