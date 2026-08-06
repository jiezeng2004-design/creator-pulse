# Security Policy

## Scope

CreatorPulse is a local-first application. Security reports are especially useful for:

- credential or session leakage through logs, diagnostics, exports, or API responses;
- unintended network exposure beyond the local machine;
- unsafe path handling around `data/` and `browser-profiles/`;
- accidental write actions against supported platforms;
- dependency or workflow issues that could expose local creator data.

## Reporting a vulnerability

Please do not publish credentials, cookies, browser profiles, databases, or an unpatched exploit in a public issue. Use GitHub's private vulnerability reporting or a private maintainer contact attached to the repository when available. Include the smallest reproducible example, affected version or commit, impact, and suggested mitigation.

When sharing diagnostics, redact values for `Cookie`, `Authorization`, `Bearer`, `access_token`, `refresh_token`, `password`, and any platform-specific session identifiers.

## Design commitments

- The server binds to localhost by default.
- Credentials are stored locally and are not returned by API read operations.
- Browser login is visible and manual; CAPTCHA and platform-control bypass are out of scope.
- Logs pass through secret redaction before they are written.
- Local databases and browser profiles are excluded from version control.
