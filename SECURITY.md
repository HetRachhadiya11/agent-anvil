# Security policy

## Supported version

Security fixes are applied to the latest `0.2.x` release.

## Trace sensitivity

Traces may contain prompts, identifiers, credentials, personal data, and tool
results. Agent Anvil applies recursive key- and pattern-based redaction before
persistence and creates artifact directories/files with POSIX modes `0700` and
`0600`. These controls reduce accidental disclosure but cannot identify every
organization-specific secret.

Do not commit raw production traces. Use synthetic or explicitly authorized,
de-identified data. Configure repository access, retention, audit logging, and
deletion according to the data owner’s requirements.

## Reporting a vulnerability

Do not open a public issue containing secrets or exploitable details. Contact the
maintainer privately and include the affected version, reproduction steps, and
impact. Send reports to `het315957@gmail.com` with the subject line
`Agent Anvil security report`.
