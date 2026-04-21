# Security Policy

## Supported versions

`sql-feature-store` is pre-1.0. Only the latest released minor version receives
security fixes.

| Version | Supported |
| ------- | --------- |
| 0.1.x   | Yes       |
| < 0.1   | No        |

## Reporting a vulnerability

Please report security vulnerabilities privately through GitHub's private
vulnerability reporting. Do **not** open a public issue, pull request, or
discussion for a suspected vulnerability.

1. Open the [Report a vulnerability](https://github.com/mshka/sql-feature-store/security/advisories/new)
   form.
2. Include as much detail as you can: affected version(s), a minimal
   reproduction, and the impact you believe it has.

### What to expect

- Acknowledgement within 7 days.
- A fix, mitigation plan, or an out-of-scope decision within 30 days where
  practical.
- Coordinated disclosure once a fix is available. Credit in the release notes
  if you'd like it.

### Scope

In scope:

- Vulnerabilities in the `sql_feature_store` package itself (e.g. SQL
  injection, schema-validation bypass, credential leakage through logs or
  errors).

Out of scope:

- Vulnerabilities in direct or transitive dependencies (SQLAlchemy,
  psycopg2, pandas, etc.) — please report those upstream.
- Issues that require an already-compromised database, credentials, or host.
- Denial-of-service from malformed input that is outside the documented API
  contract.
