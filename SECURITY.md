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
