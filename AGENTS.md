# ApplyPilot maintenance instructions

The user requests usage guidance whenever this project is upgraded or an issue is resolved.

For each feature, behavior change or bug fix:

1. Update `docs/USER_GUIDE.md` when setup, labels, controls, defaults, behavior, recovery or limitations change. Use actual control labels from the application.
2. Add a concise entry to `CHANGELOG.md` describing the final user-visible change or issue resolved.
3. Rewrite `docs/RELEASE_NOTES.md` for the release: what changed/fixed, exact usage steps, upgrade/data/dependency implications, checks actually performed and remaining limitations. Do not carry forward stale test results as if rerun.
4. The release workflow attaches USER_GUIDE.md and RELEASE_NOTES.md and uses RELEASE_NOTES.md as its release body. Keep both accurate before publishing.
5. In the completion message, link the guide/release and explain the steps affected by the change, actual verification and any material remaining limits. Distinguish tested fixtures/read-only discovery from real employer submissions or inbox consent.

Documentation-only changes do not require rebuilding application binaries or rerunning runtime tests. Verify links, names and any workflow edits instead. Use a `[skip ci]` documentation commit when the installed application has not changed. Do not claim an upgrade was installed on the user's laptop or schedule notifications merely because documentation was updated.
