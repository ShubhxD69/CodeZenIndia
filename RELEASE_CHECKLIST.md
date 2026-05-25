# CodeZen India — Release Checklist

Use this checklist before publishing any new version.

---

## Pre-Build

- [ ] Bump `APP_VERSION` in `main.py`
- [ ] Bump `APP_VERSION` in `main_window.py`
- [ ] Bump `APP_VERSION` in `updater.py`
- [ ] Update `version.json` with new version string
- [ ] Update `installer.iss` — `AppVersion` and output filename
- [ ] Write changelog text ready for `update.json`

---

## Code Quality

- [ ] `python -m py_compile main.py main_window.py editor.py terminal.py explorer.py interpreter.py settings.py syntax.py theme.py updater.py` — all pass
- [ ] No `cursor:` declarations in any stylesheet string (grep: `cursor:`)
- [ ] No deferred `import` statements inside methods
- [ ] All Qt event overrides call `super()`
- [ ] No duplicate signal connections

---

## Build

- [ ] `python create_icon.py` — `assets/icons/logo.ico` generated
- [ ] `pyinstaller CodeZenIndia.spec` — completes without errors
- [ ] `dist\CodeZenIndia\CodeZenIndia.exe` exists
- [ ] EXE launches successfully (double-click test)
- [ ] Splash screen appears and fades correctly
- [ ] All tabs, terminal, explorer, settings visible and functional
- [ ] Run a test Python script — output streams correctly
- [ ] Run a test script with `input()` — stdin accepted correctly
- [ ] Interpreter manager opens — detects at least one interpreter
- [ ] About dialog shows correct version number

---

## Installer

- [ ] `iscc installer.iss` — completes without errors
- [ ] `Output\CodeZenIndiaSetup_vX.Y.Z.exe` exists
- [ ] Installer installs cleanly to `Program Files`
- [ ] Desktop shortcut created and works
- [ ] Start Menu entry created and works
- [ ] Uninstaller removes all files

---

## GitHub Release

- [ ] Git tag `vX.Y.Z` created and pushed
- [ ] GitHub Release created from tag
- [ ] `CodeZenIndiaSetup_vX.Y.Z.exe` uploaded as Release asset
- [ ] `update.json` in repo updated with:
  - [ ] `"version"` set to `"X.Y.Z"`
  - [ ] `"download_url"` pointing to the uploaded installer
  - [ ] `"changelog"` text written
- [ ] Raw `update.json` URL returns valid JSON in browser

---

## Auto-Update Verification

- [ ] Install the **previous** released version
- [ ] Launch it — update dialog appears within 5 seconds
- [ ] Changelog text is correct
- [ ] Download completes successfully
- [ ] Installer launches automatically
- [ ] New version starts after install — correct version shown in About

---

## Final Sign-Off

- [ ] All checklist items above are ticked
- [ ] README.md reflects new features
- [ ] BUILD.md is up to date
- [ ] AUDIT_REPORT.md updated if new issues were found/fixed

---

*CodeZen India — Release Checklist v1.0.0*
