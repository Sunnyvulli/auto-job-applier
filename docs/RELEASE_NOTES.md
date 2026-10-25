# ApplyPilot — startup application learning safeguards

Correction memories on shared YC company routes now use the employer slug in the observed URL. Unscoped application routes cannot reuse memories. Sponsorship and work-authorization questions are excluded from learning and lookup of previously stored answers.

## Usage

1. Back up local application data and close the app before installing a future packaged build.
2. Review Profile and facts, then use Job library → Prepare PDFs and inspect the resume.
3. Open the actual form in the same tab, then Overview → Resume browser.
4. Review authorization and future sponsorship explicitly; these are not learned answers.
5. Select a location option, verify the attachment filename and complete CAPTCHA manually. CAPTCHA completion can expire before submission.
6. Verify a receipt before counting a confirmed submission. Record user-reported submissions separately and suppress duplicates.

See [User Guide](USER_GUIDE.md) and [Startup application playbook](STARTUP_APPLICATION_PLAYBOOK.md).

## Upgrade and dependencies

No new runtime dependencies or database migration. Existing blocked memories remain stored but are excluded from matching. No Windows binary has been rebuilt or installed. Versions remain pinned in requirements.txt; hosted browser/Gmail connectors are separate from desktop dependencies.

## Verification and limitations

Ran `python -m pytest tests/test_startup_learning.py tests/test_learning.py -q`: **22 passed**. These synthetic regressions cover employer isolation and work-eligibility learning exclusions; they do not demonstrate live ATS success. The observed Tank flow ended with a user-reported submission, without an assistant-observed receipt. CAPTCHA, login, agreements and unsupported controls can require human action. The 20–30 batch target is an operating target, not a guarantee or a newly implemented desktop scheduler.
