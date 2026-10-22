# ApplyPilot 0.7.1 — autofill and resume-upload fixes

## What was fixed

Chromium could open before the application controls rendered, leaving the form untouched. Some hidden resume/cover-letter inputs were labelled only **Attach** and were missed. An upload failure could interrupt the remaining contact fields. Some accessible identity labels were not recognized, and custom dropdowns could remain blocked after manual selection.

The browser now waits up to 12 seconds for controls, reads accessible labels/standard identity aliases, identifies Attach uploads from explicit input identity, and reports upload problems while continuing other fields. Activity shows field and document-selection counts. Supported React-select selections can be recognized after manual choice; the app does not automatically choose unknown answers. Profile now has optional explicit **First Name** and **Last Name** values.

## How to use the fix

1. Export a backup in **Diagnostics**, stop the queue and close ApplyPilot.
2. Install the updated Full/Lite installer and reopen it. No extra dependency or paid service is required. Existing profile/history normally remain in the data folder.
3. Open **Profile**, check your saved values and optionally set exact **First Name / Last Name**, then **Save profile**. Changing profile values invalidates affected draft approvals/memories until reviewed.
4. Select a job in **Job library → Prepare PDFs**, inspect the resume, and start it through the application queue.
5. Let the form load. If it opens on a description page, open the application form in that same tab, then **Overview → Resume browser**.
6. Check **Activity** and the attachment filename in the browser. A document-selection count is not a submission receipt.
7. Select any required custom dropdowns manually, then Resume. Unknown answers and verification still need your input.

See the [complete user guide](https://github.com/Sunnyvulli/auto-job-applier/blob/main/docs/USER_GUIDE.md#autofill-or-resume-upload-is-empty).

## Verification

Local browser regressions cover delayed forms, hidden Attach uploads, accessible labels/identity aliases, upload-error isolation, ambiguous files, custom-dropdown selections and native selects. The complete local suite passed **141 tests**, with five display-dependent desktop checks skipped locally. The release workflow separately gates installers on Linux/browser/desktop checks and Full/Lite installed-app checks on Windows Server 2022/2025; an additional ARM emulation job reports its own result. The installed-app smoke check now tests synthetic field filling and a hidden resume file input. Consult the linked Actions run for the actual results of this build; this text is not proof that a pending check passed.

## Remaining limits

This release does not demonstrate a completed live employer application. It cannot fill every portal or arbitrary tab, choose unknown work-authorization/sponsorship answers, resolve all custom controls, fill external embedded frames or bypass CAPTCHA/2FA. Upload failures still need review. Windows 11 x64 is the laptop target; ARM remains experimental. For a remaining failure, provide the public job URL, app version/edition and Activity message.
