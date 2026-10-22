# ApplyPilot user guide

Applies to **0.7.1**. Start here after installation. Read [release notes](RELEASE_NOTES.md) when upgrading and [version history](../CHANGELOG.md) for previous changes.

## 1. Install and open

1. Download the [Full Windows installer](https://github.com/Sunnyvulli/auto-job-applier/releases/latest/download/ApplyPilot-Full-Setup.exe). It includes Python, dependencies and Chromium. You do not need to install Python or Node.
2. Run the installer, then open **ApplyPilot** from the desktop or Start menu.
3. Use the [Lite installer](https://github.com/Sunnyvulli/auto-job-applier/releases/latest/download/ApplyPilot-Lite-Setup.exe) only when you prefer a smaller download and already have Microsoft Edge or Google Chrome installed.

Windows 11 x64 is the supported laptop target. ARM emulation is experimental. Installers are unsigned, so Windows may show a reputation warning. Internet is needed for job feeds, applications and mail. The app runs on your computer; closing it stops scheduled discovery and email sync.

## 2. Save your profile once

1. Open **Profile** and import your PDF, DOCX or text resume, or enter your details manually.
2. Review the extracted name, email, skills, summary, experience, projects and education. Scanned PDFs need text extraction/OCR before importing.
3. Optional **First Name** and **Last Name** fields let you specify the exact values for separate name fields. Leave them blank to keep the previous full-name split. Saving changed profile values invalidates earlier draft approvals and scoped memories until reviewed.
4. If you imported a PDF, decide whether to keep the original PDF for uploads. This preserves its formatting.
5. Save your profile. Name and a valid email address are required to start an application queue.
6. Add verified reusable question/answer pairs if useful. Use the fact bank for facts such as salary, start date or US work authorization. Leave unknown facts blank.

Resume import does not prove that every extracted section is correct. Check it before applying. Do not put passwords or verification codes into profile answers.

## 3. Set roles and countries

Open **Preferences**, fill the fields, then click **Save preferences**.

| Field | Example | Effect |
|---|---|---|
| Target roles | `Data Engineer, Machine Learning Engineer` | Either title phrase can match |
| Countries | `United States, India` or `US, IN` | Required for automatic discovery; either country can match |
| Cities | Leave blank, or `Dallas, Hyderabad` | Optional; country and city must match the same location option |
| Additional location keywords | Usually leave blank | Extra queue filter; older saved location preferences may still restrict results |
| Exclude companies | Optional company names | Excludes matching employers |
| Minimum matching skills | `0` for title/location discovery without a skill threshold; `1` or more for a narrower queue | Controls which imported jobs enter the application queue |
| Maximum jobs per queue | Start with `3` or `5` | Between 1 and 50 jobs |

Also review **Exclude senior / staff / manager roles**. It can exclude relevant openings if enabled. Low resource mode reduces source concurrency and page sizes. Browser choice can remain **auto**.

These are search preferences, not an assessment of your eligibility, sponsorship or work authorization.

## 4. Find and import jobs automatically

1. Open **Discover jobs**.
2. Click **Find jobs**.
3. Wait for **Search complete** in the bottom status area.
4. Read the report: listings scanned, matches, newly imported jobs and any failed company feeds.
5. Open **Job library** to inspect the imported jobs. Double-click a job to read its description and open its employer page.

You do not need to add the built-in catalog companies individually. Version 0.7 searches **37 catalog companies plus your saved sources**, using Greenhouse, Lever, Ashby and SmartRecruiters public employer feeds. It does **not** search every company, LinkedIn, Indeed or every Workday site.

A job needs explicit country evidence in its location or structured employer data. City-only, state-only, unknown-country and worldwide-only listings are excluded rather than assigned a country by guesswork. Leaving Cities blank gives broader coverage. Repeating a search imports only new URLs; zero new imports can mean all matches were already saved.

Optional: enable **Find new jobs every 15 minutes while ApplyPilot is open (import only)**. This does not start applications automatically.

To expand coverage, open **Sources**, select the provider, enter a company board identifier or supported board URL, then **Add company**. Automatic discovery will include that source next time. This is optional for companies already in the catalog.

## 5. Review and tailor documents

1. Select a job in **Job library**, then click **Tailor application**.
2. Under the job-description tab, confirm the actual description or paste it if missing. Click **Save description + generate draft**.
3. Review **Resume & letter** and **Changes & evidence**. Edit any proposed text that needs correction.
4. Click **Approve resume & letter** when the documents are accurate.
5. If you kept an original PDF but want the tailored version for this job, check **Use this generated resume PDF for this job** before approving.
6. Use **Prepare PDFs** and open the documents to inspect them before starting your first application.

Tailoring uses your saved facts, extractive selection and local templates. It does not invent experience or run an unrestricted AI rewriting service. Without an approved job draft, the normal original-PDF/base-document workflow applies. Changing your profile, facts or job description can invalidate earlier approvals; reopen and review the draft.

For a custom question: open **Questions**, select or paste the question, choose **Draft answer**, review/edit it, then **Approve this answer for this job**. Unsupported or unanswered questions pause for your input.

## 6. Start applications

For a first run:

1. Open **Overview** and leave automatic submission unchecked.
2. Click **Build queue**, inspect the jobs, and use **Remove selected** for any you want to omit.
3. Click **Start my queue**. The visible browser opens employer/ATS application links and fills supported fields.
4. Check the uploaded resume, answers and application details. Follow the app's pause messages.

For later runs, **Discover jobs → Find & apply** performs discovery and starts a bounded queue restricted to that search's results. It uses the current saved skill and preference filters. It does not apply to every imported listing automatically; the queue cap and current job status still apply.

To enable unattended submission on supported forms, check **Submit supported forms automatically using my saved answers** on Overview. This is opt-in and limited to recognized Lever/Greenhouse forms. Other portals use assisted completion. Unknown questions, registration, custom controls and verification can still pause the browser. An all-failed or zero-match search cannot start unrelated old library jobs.


### Autofill or resume upload is empty

1. Check **Profile → Save profile** after importing or editing your details. Importing into the editor alone is not saving.
2. Select a job in **Job library**, choose **Prepare PDFs**, and inspect the documents. If using an original resume, its selected file must still exist.
3. Start the application from ApplyPilot's queue. It fills the browser tab opened for that job; it does not automatically fill arbitrary tabs you open yourself.
4. Allow up to 12 seconds for a delayed form to appear. If you are still on the job-description page, open its application form in the **same tab**, then click **Overview → Resume browser**.
5. Check **Activity** for `Filled … fields; selected … documents for upload`. Selection counts mean that the browser accepted a file selection, not that an employer accepted the application. Check the attachment filename in the browser.
6. In 0.7.1, hidden resume/cover-letter inputs labelled **Attach** are identified using their explicit input identity. An unclear upload type, missing file or upload failure is reported for manual review while other fields keep filling.
7. Select required custom dropdowns such as country/city manually, then **Resume browser**. Supported React-select chosen values can be recognized; merely typing into a search field is not selecting an option. Unsupported controls and external embedded forms still require manual completion.
8. Keep automatic submission off while checking the first application after upgrading. Uploading a resume does not imply submission.

If the exact form still does not fill, report its public job URL, the app version/edition, Activity message, and which fields/uploads remained empty. Include a redacted screenshot if useful; do not share passwords, verification codes or private resume contents in a public issue.

## 7. Resolve a pause and teach an answer

1. Keep the application browser open and read the status message/Activity entry.
2. Fill or correct the missing eligible text field, native dropdown or labeled native radio group in that browser.
3. Click **Resume browser** in Overview **before clicking Next or Submit in the browser**, so the app can observe the corrected field.
4. With learning enabled, a changed answer is saved as pending. A positive submission confirmation activates it for matching future applications.
5. Inspect saved learning under **Job library → Learned answers** or **Preferences → Learned answers**. You can disable, forget or explicitly enable reviewed entries.

Reuse is deliberately restricted to matching employer, role, location, question/control choices and unchanged profile/facts. It is not universal learning from every problem. Profile changes and memory age can require review. Copy a memory to Profile answers only if it is also valid across employers and roles.

CAPTCHA, passwords, 2FA codes, consent and protected personal questions are not learned. Complete CAPTCHA/2FA or device approval yourself, then resume. To use account assistance, select the job and open **Account tools**; save credentials for the exact portal origin, then use **Fill account** during a pause. Registration still needs your review. Shared ATS hosts can require different employer accounts; enter those directly when needed.

**Fetch email code** is an optional helper requiring connected mail, the approved sender and current portal context. It fills a supported fresh code only after your request; it does not bypass authentication or submit the code automatically.

## 8. Track results and email

| Job status | What to do |
|---|---|
| saved | Imported; not applied |
| prepared | Documents prepared; not proof of submission |
| running | Being processed by the browser |
| needs_attention | Read the message and resolve the pause |
| submitted | Positive confirmation detected or status manually set; check the portal/receipt if unsure |
| uncertain | Submission outcome is unclear or a session was interrupted; check the employer portal before retrying |
| interview / rejected / closed | Tracking statuses you can update after verifying the outcome |

Use **Job library → Set status** for a verified manual update. Submitted and uncertain jobs are protected from automatic queue retries. View **Activity** for messages and **Export application CSV** for a history export.

Email is optional and does not block job discovery:

- **Gmail OAuth:** follow [Gmail setup](GMAIL_SETUP.md), then in **Inbox** use **Google client JSON → Connect Google → Sync**. You must configure your own Google Desktop OAuth client once; the ChatGPT Gmail connection is separate.
- **IMAP:** choose the provider, enter the email address, use **App password**, then **Sync**. Use a provider-generated app password where supported.
- **Offline review:** **Import email** accepts `.eml` files.

Optional five-minute mail sync works while the app is open. Double-click messages to read them. Labels and job matching are advisory. **Compose follow-up** opens an editable message; replace placeholders, check the recipient and explicitly confirm sending. Email is never sent automatically. Gmail sending also needs the optional **Allow sending** permission.

## 9. Upgrade and back up

Before installing a new version:

1. Read its release notes: what changed, how to use it, upgrade steps, actual checks and remaining limits.
2. Stop the browser queue and wait for background tasks to finish.
3. Open **Diagnostics → Export backup** and save a private `.applypilot` file.
4. Close ApplyPilot, install the new Full or Lite installer, then reopen it.
5. Check Profile, Preferences, Job library and any changed settings. Inspect one application before resuming automatic submission after a behavior change.

Your data normally remains under `%LOCALAPPDATA%\ApplyPilot`. Exported backups include personal profile/history/mail data and are not encrypted. Passwords, OAuth credentials and browser sessions are excluded. A daily local backup retains five daily dates; it is not an off-device copy.

To restore, stop all work and use **Diagnostics → Restore backup**. Restore replaces the workspace after validation and saves a recovery copy first. The app closes; reopen it and reconnect email/accounts. Submission, learning and recurring work start disabled, and document approvals need review again. Do not restore an older backup simply to retry an uncertain application; first check the employer portal to avoid a duplicate.

## 10. Common problems

| Problem | Check or action |
|---|---|
| No jobs found | Save roles and countries, clear Cities/additional location keywords, check seniority exclusions and read source errors. Unknown-country listings are excluded. Coverage is finite. |
| Jobs imported but the queue is empty | Check minimum skills, exclusions, city/location filters and job statuses. Try minimum skills `0` if you want role/location matching alone. Some feed summaries lack full descriptions. |
| Zero newly imported jobs | Matches may already be in the library. Check total matches and search Job library. |
| A company feed failed | Read its source report entry. Other sources continue; a retired or changed board may need a corrected source or software fix. |
| Browser will not open | Check **Diagnostics** and **Preferences → Application browser**. Full includes Chromium; Lite needs installed Edge/Chrome. Stop existing work before retrying. |
| Autofill/upload stays empty | Follow the dedicated troubleshooting steps above; save Profile, prepare PDFs, use the queue tab and read Activity. |
| Resume missing or wrong | Check the selected original PDF still exists, the job-specific PDF toggle and draft approvals; regenerate and inspect documents. |
| Application pauses repeatedly | Correct the identified field and Resume before advancing. Custom controls, changed portal workflows and verification may need manual completion or a software fix. |
| Submission outcome unclear | Check the employer portal and confirmation email; keep the job uncertain until verified. Do not reset it just to force a retry. |
| Email will not connect | Check provider/authentication, OAuth setup or app-password support. Reconnect after restore. Discovery can still be used without email. |
| App feels slow | Enable low resource mode, reduce the queue size and close extra browser windows. Check available RAM/disk in Diagnostics. |

For an issue report, provide the app version/edition, Windows version, action taken, expected/actual result, relevant Activity text, source/portal domain and reproduction steps. Share a redacted screenshot if useful. Exclude passwords, codes, tokens, resume contents and private inbox data. A bug report does not automatically send diagnostics or personal files.

## Validation limits

The 0.7.1 autofill changes have browser regression checks for delayed rendering, Attach-labelled hidden inputs, accessible labels/identity aliases, upload-error isolation, ambiguous uploads and manual custom-dropdown selection. Installed-app checks exercise autofill and hidden uploads with synthetic data. These are controlled tests, not a completed live employer application. Check each release workflow for its actual installer results.

For the 0.7 discovery release, 132 tests passed plus five desktop checks; Full/Lite installed-app checks passed on Windows Server 2022/2025 and Windows 11 ARM emulation. A live read-only discovery run scanned 16,570 listings and found 123 matches for Data Engineer/Machine Learning Engineer in US/India with seniority exclusion off. Counts change over time. These checks do not prove universal portal support. Real employer submissions, your live inbox and account registration remain unvalidated.
