# ApplyPilot 0.3

A free local Windows workspace for finding jobs, preparing applications and tracking replies. A native sidebar dashboard, light/dark themes and preference-based queues reduce repeated entry. No paid AI API, hosted server or CAPTCHA-solving subscription is configured.

## Download

- **[Full installer](https://github.com/Sunnyvulli/auto-job-applier/releases/latest/download/ApplyPilot-Full-Setup.exe)** — includes Python, dependencies and a browser. Recommended for first use.
- **[Lite installer](https://github.com/Sunnyvulli/auto-job-applier/releases/latest/download/ApplyPilot-Lite-Setup.exe)** — smaller package with Python/dependencies; uses your installed Microsoft Edge or Google Chrome. It does not download a browser on first launch.

Install and open ApplyPilot. No Python or Node installation is required. Both editions install for your Windows user without administrator access. Internet is required for jobs and email. The installers are unsigned; Windows can show a reputation warning. Close the app before upgrading. Profile/history stay under `%LOCALAPPDATA%\ApplyPilot`, separately from application binaries.

## A shorter daily workflow

1. **Profile:** import a PDF, DOCX or text resume, review the extracted sections, then save. For PDFs, optionally keep the original file and formatting for applications. You can also edit the profile manually. Resume extraction is heading/contact based and requires review; scanned files need OCR first.
2. **Preferences:** set target role keywords, locations, excluded companies, minimum skill overlap and a queue limit. Turn on low resource mode if needed. Matching is a keyword/preference filter, not proof of eligibility or sponsorship.
3. **Sources:** add companies with simple controls or use the starter companies. Refresh all saved feeds together. Source imports are independent of application submission.
4. **Overview:** build a queue to review the matching jobs, or click **Start my queue**. A reviewed pending queue is preserved when started. With no pending queue, the button builds one using your saved preferences. Only saved/prepared jobs can enter an automatic plan.
5. **Browser:** review mode is the default. Optional automatic submission uses your saved facts on supported forms. Unknown questions, account registration and verification pause for you. Reusable answers can be added in Profile without writing JSON.

The dashboard shows your library, prepared documents, applications needing input and submissions. Search is debounced and lists are paginated. Job details use readable descriptions. PDF preparation runs in the background. Unchanged document sets are cached and verified with hashes before reuse.

## Coverage

| Area | Implemented behavior |
|---|---|
| Job feeds | Greenhouse, Lever global/EU, Ashby, SmartRecruiters |
| Applications | Exact labeled text fields, native selects, hidden/visible resume uploads, multi-step Next/Continue |
| Automatic submission | Opt-in for recognized Lever/Greenhouse forms; other portals use assisted completion |
| Documents | Factual profile-derived PDFs/text, or original imported PDF plus a factual cover letter |
| Accounts | Generate/save passwords in OS vault; fill only an explicitly approved exact HTTPS origin, top frame only |
| Registration | Review terms and submit registration in the browser; unattended signup is not implemented |
| Email verification | User-requested retrieval/filling of one fresh six-digit code from an approved sender for the current origin |
| CAPTCHA, SMS, device approvals | Complete in the same visible browser and resume; no bypass |
| Email | Gmail OAuth, IMAP app password or .eml import; optional five-minute sync while open |
| Follow-ups | Editable draft and explicit Send confirmation; OAuth send permission is optional |
| Saved sources | Optional 15-minute refresh while open; up to three sources concurrently, one in low resource mode |
| Tracking | Receipt JSON, timestamps, notes, conservative positive-confirmation detection and CSV export |
| Duplicate protection | Unique URLs, atomic claims, no automatic retries of submitted/uncertain jobs, interruption recovery |

Starter sources are editable examples, not a complete employer directory or eligibility recommendations. This is preview software. No real employer submissions, account registrations or user Gmail consent have been performed by the developer. Fixture tests are not live-portal certification.

## Performance

Bulk imports use one transaction, indexes and SQLite WAL. List views load at most 100 rows (50 in low resource mode), without large job descriptions. Queues stream candidate records in batches and cap at 50 jobs. Network requests reuse connections with bounded retries for transient GET failures. One browser context processes applications sequentially.

A synthetic Linux development benchmark with 10,000 jobs measured:

| Check | Observed result |
|---|---:|
| Bulk import, 10,000 jobs | 0.195 seconds |
| Page of 100 jobs, median | 0.634 milliseconds |
| Preference scan, 10,000 jobs | 0.099 seconds |
| Bulk versus separate commits, 1,000 jobs | About 70× faster |

These are local synthetic measurements, not laptop guarantees or network/application timings. Reproduce with `PYTHONPATH=. python benchmarks/run.py`; raw results are in [benchmarks/results-linux.json](benchmarks/results-linux.json).

## Windows compatibility

The supported laptop target is **Windows 11 x64**. The installer permits Windows 11 ARM x64 emulation, with a separate experimental ARM check. Legacy 32-bit Windows and Windows 7/8 are unsupported. Windows 10 is not a supported/tested laptop target. Using a different browser does not remove OS or device requirements.

Full and Lite installer checks run on Windows Server 2022 and 2025. A separate Windows 11 ARM job reports emulation results; inspect that job before treating ARM as validated. These VMs do not represent every laptop, display scale, driver or corporate policy. Low resource mode reduces local work; a physical 4 GB laptop has not been measured. An 8 GB laptop with a modern browser is a practical target, not a guaranteed minimum.

The window adapts to screen dimensions and pages scroll when needed. Development interaction checks cover 1240×820, 1024×700 and 960×640 windows. Windows uses Segoe UI and enables system DPI awareness. Diagnostics reports RAM, free disk, architecture and browser packaging locally. No telemetry is sent.

## Email and accounts

For Gmail OAuth, follow [one-time setup](docs/GMAIL_SETUP.md). You must register/import your own Google Desktop OAuth client and complete consent. The ChatGPT Gmail connection cannot be reused by this app. Tokens/client configuration and portal passwords use the OS keyring. SQLite contains readable profile/mail/receipt data; protect your Windows account and disk.

IMAP requires provider-supported app-password login. Outlook OAuth is not implemented. Optional mail sync reads recent messages without marking them read. Classification and job matching are advisory; ambiguous matches stay unlinked. Email never sends automatically.

Account tools remain available from Job library. Shared ATS hosts can have employer-specific accounts; the current vault mapping holds one account per origin. Use direct browser entry when tenant accounts differ. Verification helpers do not solve CAPTCHAs or device approvals and do not submit a retrieved code automatically.

## Development

Python 3.12 and a desktop display are needed for source. Windows installer users skip these commands.

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
python -m playwright install chromium
python -m pytest -q
python launcher.py
```

Linux also needs Tk and browser system dependencies. Desktop interaction tests require a display (for example `xvfb-run -a python -m pytest tests/test_desktop.py -q`). [Actions](https://github.com/Sunnyvulli/auto-job-applier/actions) gates release on Linux/browser checks plus Full/Lite installation and packaged-app checks on both Windows build images. ARM is separately reported and remains experimental. Releases include SHA256 checksums. See [validation](VALIDATION.md) and [security](SECURITY.md).

GitHub hosts source/installers. The agent runs on your computer; GitHub Pages cannot host its backend. No paid infrastructure is provisioned. GitHub runner availability/policies still apply.

MIT licensed. Dependencies retain their licenses; browser licensing files ship in Full. Uninstall leaves personal data for recovery; remove the data folder separately to erase it.
