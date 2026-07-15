---
name: code-review
type: knowledge
version: 1.0
agent: Manus
triggers:
  - review
  - bug
  - regression
  - security
  - test
---
Code review workflow:
1. Prioritize correctness, regressions, missing tests, and security issues.
2. Ground findings in exact files, functions, or observable behavior.
3. Verify suspicious behavior by reading the caller and callee, not just one file.
4. Keep style-only notes secondary unless they block maintainability.
5. When implementing fixes, run focused tests and inspect the resulting diff.
