# Security Policy

## Design notes

- **Skills are plain text.** Every skill in this repository is a human-readable
  `SKILL.md` file with no executable payload. You can — and should — audit any
  skill before installing it into your agent environment. There is no compiled
  or obfuscated content anywhere in the skills library.
- **API keys stay local.** Quorum reads provider credentials from environment
  variables (or a local `.env`, which is gitignored). Keys are never written to
  engagement output, memory files, or logs.
- **Engagement output is local-only.** Reports, working papers, and the memory
  layer are written to your filesystem. Nothing is uploaded anywhere except the
  model API calls you configure.

## Reporting a vulnerability

Please do not open a public issue for security problems.

- Email: security@quorum-firm.dev
- Or use GitHub's private vulnerability reporting on this repository
  (Security tab → Report a vulnerability).

Include a description, reproduction steps, and the affected version. We will
acknowledge reports within 48 hours and aim to ship a fix or mitigation within
14 days for confirmed issues. Reporters are credited in release notes unless
they prefer otherwise.

## Supported versions

Only the latest minor release receives security fixes while the project is
pre-1.0.
