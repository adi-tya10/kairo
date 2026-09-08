# KAIRO: Coverage Enforcement & CI Quality Gates

> **Domain:** Quality Assurance & Testing  
> **Document ID:** KAIRO-QA-GATES  
> **Standard:** Zero-Warning Linter & 85%+ Code Coverage

---

## 1. Quality Gates Pipeline

```
[Lint & Style]     ──► Ruff (Python) & ESLint / Prettier (TypeScript)
[Static Types]     ──► mypy strict (0 errors) & tsc
[Unit Coverage]    ──► Overall >= 85% line coverage
[Anomaly Coverage] ──► 100% branch coverage on HW-01 through HW-05
[Security Scans]   ──► TruffleHog (0 secrets) & pip-audit (0 CVEs)
```

Direct pushes to `main` are blocked until all 5 gates pass on PR.
