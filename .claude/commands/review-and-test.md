---
description: "Run the full review pipeline: code review, security audit, then test verification. Use after implementing changes."
allowed-tools: Read, Grep, Glob, Bash, Edit, Write
---

# Review & Test

Run the full Aasan review pipeline on recent changes:

1. **Code Review**: Use the code-reviewer agent to review the git diff for quality, type safety, money handling (paise), and existing patterns.
2. **Security Audit**: Use the security-auditor agent to check for auth vulnerabilities, PII exposure, input validation, and network security.
3. **Test Verification**: Use the tester agent to run/verify tests (pytest for backend, Jest/RTL for frontend). Write missing tests if needed.
4. **Summary**: Provide a final summary with critical issues, warnings, and test results.