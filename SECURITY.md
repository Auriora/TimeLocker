# Security Policy

## Supported Versions

Use this section to tell people about which versions of your project are currently being supported with security updates.

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| 0.1.x   | :white_check_mark: |
| < 0.1.0 | :x:                |

## Reporting a Vulnerability

TimeLocker takes security issues seriously. We appreciate your efforts to responsibly disclose your findings.

### How to Report a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to [security@example.com](mailto:security@example.com). If possible, encrypt your message with our PGP key.

Please include the following information in your report:

- Type of issue (e.g., buffer overflow, SQL injection, cross-site scripting, etc.)
- Full paths of source file(s) related to the manifestation of the issue
- The location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit the issue

### Response Process

After you have submitted a vulnerability report, you can expect the following process:

1. Acknowledgment: We will acknowledge receipt of your vulnerability report within 48 hours.
2. Verification: We will work to verify the issue and may ask for additional information.
3. Remediation: Once verified, we will develop and test a fix.
4. Disclosure: We will coordinate with you on the disclosure timeline.

### Disclosure Policy

- We will work with you to understand and resolve the issue quickly.
- We will validate and confirm the problem.
- We will address the issue as quickly as possible, usually within 90 days.
- We will handle your report with strict confidentiality and not pass on your personal details to third parties without your permission.

## Security Measures

TimeLocker implements several security measures to protect your data:

- End-to-end encryption for all backup data
- Secure credential storage using OS keyring
- Regular security audits and code reviews
- Dependency vulnerability scanning

## Security Best Practices

When using TimeLocker, we recommend the following security best practices:

- Use strong, unique passwords for repository encryption
- Keep your TimeLocker installation updated to the latest version
- Follow the principle of least privilege when configuring access permissions
- Regularly audit your backup configurations and access logs

## Security Updates

Security updates will be released as part of our regular release cycle or as emergency patches for critical vulnerabilities. We will announce security updates through:

- GitHub releases
- The project's security advisories
- Email notifications to registered users (for critical updates)

Thank you for helping keep TimeLocker and our users safe!