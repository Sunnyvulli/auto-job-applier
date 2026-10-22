# Security review — 0.1 preview

This is an implementation review by the builder, not an independent penetration test or security certification.

## Controls implemented

- No inbound HTTP service and no default cloud data transfer.
- Desktop single-instance lock protects one browser profile from concurrent use.
- TLS for public API reads, IMAP and SMTP.
- Mail app passwords held by operating-system keyring, not committed or saved in SQLite.
- Browser-managed sessions; Chromium sandbox explicitly enabled for the production browser worker.
- Imported content cannot invoke shell commands. File opener uses fixed subprocess argument lists.
- SQL uses bound parameters; board identifiers are restricted before interpolation into fixed API hosts.
- CSV formula prefixes are escaped.
- Upload selection is restricted to generated resume/cover-letter paths.
- No implicit consent, sensitive answer guessing, automated demographic answers or CAPTCHA evasion.
- Atomic application claims, process interruption recovery and no automatic retry of uncertain/submitted records.
- Email sends require an explicit recipient and confirmation.

## Remaining exposure

SQLite contains readable profile information and email bodies. Browser cookies and receipt text are sensitive files. The app relies on the security of the user's Windows account and storage. It is not a hardened multi-user workstation service. Employer pages still run third-party JavaScript inside Chromium; phishing protections and judgment remain necessary.

Submission detection is a conservative text/DOM heuristic, not a server-side application receipt API. Live form changes, embedded custom controls and browser fingerprint restrictions can cause failure. False negatives are expected and should be checked manually before retrying.

No live accounts, real mail credentials, employer applications or authentication challenges were exercised during fixture tests. Release publication is gated on tests and Windows install/start smoke test, not a claim of independent validation.

## 0.2 additions

- SQLite connections now close deterministically after every transaction.
- New public feed hosts are fixed in code; board URL parsing verifies provider hostnames and restricts company identifiers. SmartRecruiters pagination rejects repeated pages instead of silently claiming a complete import.
- Account passwords are generated using Python secrets and stored in OS keyring. Helpers require an explicitly configured exact HTTPS origin and fill only the top page. Registration/consent remains manual. Shared-host tenant separation remains a documented limitation.
- Verification codes require explicit user action, an origin-specific approved sender, matching recipient, recent date and unambiguous six-digit content. Codes are not logged or placed in SQLite. Sender/date checks are conservative filters, not a cryptographic guarantee of message authenticity. Codes are filled only in explicit OTP controls; no authenticator/SMS/CAPTCHA bypass is implemented.
- Gmail Desktop OAuth configuration must use official Google authorization/token endpoints. Tokens and client configuration use the OS vault. Read-only scope is default; sending is optional and still manually confirmed. A temporary loopback callback is opened only during Google consent. This is the exception to the earlier no-listener description.
- Recurring source/mail checks are opt-in and run only while the application is open. They do not authorize automatic applications or replies.

New account helpers and email-code handling have fixture coverage. Real registration, live user OAuth consent and real mailbox-code handling require user-side validation; no such live success is claimed.

## 0.3 additions

Resume import reads local PDF/DOCX/text with file/page limits and requires human review. It does not execute macros or request an external AI service. The original PDF is copied only on explicit use of that option. Application documents remain factual templates or that approved original file.

Cached documents are keyed by profile/job/template/source fingerprints and verified by file hashes. Bulk inserts validate URLs before beginning the transaction. WAL and pagination change performance, not application authorization. Preference plans exclude running, uncertain and submitted jobs. Automatic submission still requires the user's saved opt-in.

Lite selects an installed Edge/Chrome browser. Browser profiles remain separate per engine. Full carries a tested pinned browser; choosing a system browser allows that browser's normal updates. No compatibility with arbitrary browser versions or legacy OSes is guaranteed. HTTP connection pooling is restricted to GET feed requests with bounded retries; it does not retry application POSTs.


## 0.4 review

Form data and resume uploads are restricted to the main page and same-origin frames; cross-origin and opaque frames are skipped. This does not verify the trustworthiness of a user-selected portal. Local backup archives use a fixed file allowlist, bounded sizes, verified hashes and validated data records, with no SQL or archive path extraction. They include personal profile and email content and are not encrypted. OS vault secrets and browser sessions are excluded. Integrity hashes are not signatures. Restore requires an idle app and an explicit in-app replacement confirmation, saves a safety copy, and disables unattended settings. Existing generated documents/receipts are archived separately. No independent security audit has been performed.


## 0.5 drafting boundaries

Job-specific drafts and fact-bank values are local readable personal data. Generated proposals are not browser answers until explicitly approved for an exact normalized label and job. Resume/cover-letter edits require separate approval. Changing profile, job description, fact bank or selected original resume invalidates approvals; stale approved documents stop until reviewed or cleared. The local engine uses no remote model endpoint and treats job descriptions as matching text. It does not verify user-entered claims. Restoring data disables all draft approvals. Optimistic revision checks prevent stale editor windows or browser question capture from overwriting newer approvals. Existing global exact answers remain available because the user explicitly saved them. Unsupported controls and verification still pause for manual completion.


## 0.6 answer learning

Clicking Resume with learning enabled authorizes capturing changed visible eligible answers on the unchanged page URL. The capture filter excludes credentials, codes, authentication, contact/security identifiers, protected demographic/medical information, references and consent; checkboxes/files are excluded. Learning reads only the main page and same-origin frames, rejects duplicate question labels, and retains only native-valid changes to unchanged control/choice structures. Pending answers stay on their source job until positive confirmation, unless explicitly enabled by the user. Future reuse is limited by employer, role, location, question, control choices, profile/fact fingerprint and 90-day age. The scope is not proof that two questions have identical legal meaning: users remain responsible for their answers. Explicit copying to global Profile answers removes scope restrictions. Memories contain readable personal data; backups restore them disabled. Native radio automation requires one clearly labeled fieldset/group, exact option text, and excludes sensitive/consent groups. This feature does not learn CAPTCHA, authentication secrets, arbitrary scripts or portal navigation workflows.
