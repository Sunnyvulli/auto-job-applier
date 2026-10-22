# ApplyPilot 0.6

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

Saved queues are rechecked against your current preferences and application status when started. Select jobs in the overview queue and use **Remove selected** to leave them out. Ranking keeps only the best 50 candidates in memory.

The dashboard shows your library, prepared documents, applications needing input and submissions. Search is debounced and lists are paginated. Job details use readable descriptions. PDF preparation runs in the background. Unchanged document sets are cached and verified with hashes before reuse.

## Coverage

| Area | Implemented behavior |
|---|---|
| Job feeds | Greenhouse, Lever global/EU, Ashby, SmartRecruiters |
| Applications | Exact labeled text fields, native selects/radio groups, hidden/visible resume uploads, multi-step Next/Continue; approved job-specific and confirmed learned answers |
| Automatic submission | Opt-in for recognized Lever/Greenhouse forms; other portals use assisted completion |
| Documents | Base templates or reviewed job-specific resume/letter PDFs; original-PDF override is explicit per job |
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

## Automatic mode with learning

After setup, enable **Submit supported forms automatically** on Overview and start your queue. Supported known forms are filled and submitted sequentially. If a form needs help, the app keeps the browser open and pauses. This is supervised automation with reusable answer memory, not guaranteed unattended operation across every portal.

**Teach an answer:** fill or correct a visible text field, native dropdown or labeled native radio group, then click **Resume before clicking Next or Submit**. With learning enabled (the default), only changed eligible answers are stored. Pending answers can be reused on that same job; a positive submission confirmation activates them for later matching jobs. A correction to an old learned answer retires the old value immediately. A stalled automated action disables memories used on that step rather than blindly retrying them.

Automatic reuse requires the same employer scope, exact normalized question, role title, location, control type, choice labels and unchanged saved profile/fact bank. Memory needs review after 90 days. Shared ATS hosts are separated by employer path; ambiguous embed/login paths do not learn. Explicit job-specific answer approvals take priority. No fuzzy question inference, model training or remote service is involved.

Open **Job library → Learned answers** or **Preferences → Learned answers** to inspect, disable, forget or explicitly enable reviewed memories. You can copy selected answers into global **Profile answers** for cross-employer reuse; do this only when the answer is valid beyond the original employer, role and location. Profile changes then invalidate old scoped memories and job drafts until reviewed again. Turning learning off disables both capture and learned-answer reuse.

Passwords, codes, CAPTCHA, account/security identifiers, contact details, consent, demographic/medical information and reference questions are excluded from capture. File uploads and checkboxes are not learned. Unsupported custom controls, CAPTCHA/2FA, registration, portal redesigns, ambiguous action buttons and server failures can still need your intervention; correcting them does not train new portal workflows. If you advance or submit before Resume, disappeared fields cannot be learned. A manual enable in the memory manager is an explicit override of the confirmation gate. Backups retain memory as disabled records; restore turns learning and automatic submission off.

## Tailor a resume and answer custom questions

1. Save your factual background under **Profile**. Optionally add verified facts such as salary, start date or US work authorization using the fact-bank selector. Facts help propose answers; they do not authorize filling a new question automatically.
2. In **Job library**, select a job and open **Tailor application**. Paste or edit the actual job description, then choose **Save description + generate draft**. This stores the description locally for matching and drafting.
3. Review **Resume & letter** and **Changes & evidence**. The local engine prioritizes verified matching skills, adds an application-specific strengths sentence, ranks existing project paragraphs and drafts a factual cover letter. Employment blocks and education are preserved. The possible-gap list uses a fixed technology vocabulary and is not an exhaustive eligibility assessment.
4. Edit the proposed sections if needed, verify every claim, then **Approve resume & letter**. Your master profile stays unchanged. If an original PDF is configured, it remains selected by default; explicitly check **Use this generated resume PDF for this job** to apply the reviewed resume instead. Without an original PDF, generated-draft mode is selected by default. Preparing PDFs or resuming the browser uses only approved document edits.
5. Under **Questions**, paste a question or select one detected when the browser paused. Choose **Draft answer**, review the proposed text and its evidence/missing-information note, then **Approve this answer for this job**. Only that exact normalized question label on that job can reuse the approval. Use **Revoke this answer** to remove it. During an application, **Overview → Review drafts** opens the latest paused job or the selected queue job.

This runs locally with no model/API subscription. It uses extractive selection, ranking and templates; it does not perform unrestricted language-model rewriting. Free-form edits are user-authored and require your factual review. No ATS score or employer acceptance is promised.

Questions without supporting facts stay blank. Sponsorship, authorization, salary, years, personal motivation, credentials and demographic questions are not inferred from a resume. Country-specific US facts do not answer other countries' questions. Specific technology-experience questions need verified skills and a supporting saved example. Checkboxes, unsupported radio layouts, unsupported controls and CAPTCHAs still require manual attention. Overlong approved answers pause rather than being silently truncated.

Profile, fact-bank, original-PDF and job-description changes invalidate prior approvals. An old draft can be reopened as an unapproved proposal and regenerated or reviewed again. Concurrent edits are rejected instead of overwriting a newer revision. Restored backups preserve draft text and facts but disable all draft approvals. Clear a job draft to return to base documents/answers.

## Backups and recovery

Open **Diagnostics → Export backup** to save a `.applypilot` archive. A daily local backup is also made shortly after startup; the five most recent daily dates are retained under your private data folder's `backups` directory. They are local recovery copies, not off-device protection. A failed backup is reported in Activity.

Backups include your saved profile/answers, fact bank, job-specific drafts, preferences, sources, queue, jobs/status/events, stored email messages, scoped answer memory and selected original resume PDF. Older backups without drafts remain accepted. They exclude browser cookies, portal vault entries, Gmail OAuth credentials, mail connection settings, generated documents and receipt files. **Backups are not encrypted and include personal information.** Keep exported copies somewhere private.

**Diagnostics → Restore backup** validates file names, size limits, hashes, record structure and job identities before replacement. Stop the browser and wait for background work first. Restore saves the current workspace into a separate recovery archive and moves existing generated documents/receipts into a recovery folder so old receipts are not confused with restored history. A database failure rolls back the transaction and restores that folder. After success the app closes; reopen it and reconnect email/accounts. Automatic submission and recurring imports/mail sync start disabled. Submitted jobs stay protected; interrupted jobs become uncertain and require checking the portal. Generated documents are rebuilt as needed. SHA256 checks detect damage; they do not prove who created an archive. Import backups only from a trusted source.

Application filling uses the main page and frames with the exact same origin. External and opaque embedded frames require manual entry. If a profile or original resume changes during a paused step, documents refresh before the next fill. A missing selected original PDF stops preparation instead of silently substituting a generated resume.

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
