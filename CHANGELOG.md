# Changelog

All notable changes to BRL-305 Monitor are documented here.
Format follows Keep a Changelog; versioning follows SemVer.

## [Unreleased]

## [1.1.0] - 2026-07-08
### Added
- Per-inspector ERPNext sign-in (session auth): each inspection is recorded under the logged-in user, with a Switch user action for shift change.
- CustomTkinter UI redesign on the Sanad slate palette; light theme by default with a dark toggle.

### Changed
- ERPNext client now supports session login (username/password, cookie + CSRF) alongside token auth.
- The integration round-trip test uses the session login and is verified green against newjacquard.

## [1.0.0] - 2026-07-08
### Added
- ERPNext inspection tunnel: pushes each roll's length, weight and defects into prime_textile's existing inspection API (get_inspection_context, save_inspection, finalize_inspection) with no ERPNext changes.
- Offline store-and-forward outbox (SQLite) with retry and dead-letter; exactly-once via idempotent-per-Job-Card server methods.
- ERPNext tab, Config settings, and SerialHandler.read_full_roll (length, weight and defects in one read).
- Windows 7 guardrail: stdlib urllib and ssl (no requests), certifi bundled in the PyInstaller spec, and a startup preflight that names a missing ssl/sqlite3/certifi DLL instead of crashing.
- Minimal Inno Setup installer (Setup.exe) built by GitHub Actions (32-bit) with the VC++ 2015-2022 x86 runtime; the build silent-install-tests the result before publishing.
