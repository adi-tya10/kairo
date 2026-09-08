# Contributing to KAIRO

Thank you for your interest in contributing to **KAIRO**! We welcome contributions from engineers, researchers, and technical writers. 

This document outlines our engineering standards, branching strategy, commit conventions, code formatting rules, and review process.

---

## 1. Code of Conduct

We are committed to providing a friendly, safe, and welcoming environment for all contributors. Respect, constructive feedback, and ethical engineering practices are mandatory.

---

## 2. Branching Strategy (Trunk-Based Development)

We follow **Trunk-Based Development** with short-lived feature branches:

```
main ───────────────────────────────────────────────► (Always Deployable)
       │                        ▲
       └──► feat/jira-sync ─────┘ (PR with CI Pass & Approval)
```

* **Main Branch (`main`):** Production-ready, always passing CI/CD checks. Direct pushes to `main` are blocked.
* **Branch Naming Conventions:**
  * `feat/<short-description>`: New features (e.g., `feat/github-app-webhook`)
  * `fix/<issue-key>-<short-description>`: Bug fixes (e.g., `fix/hw01-status-parsing`)
  * `refactor/<module>`: Code restructuring (e.g., `refactor/neo4j-service`)
  * `docs/<topic>`: Documentation updates (e.g., `docs/api-spec-v1`)
  * `test/<component>`: Test coverage additions (e.g., `test/cv-pipeline-mock`)

---

## 3. Commit Message Conventions (Conventional Commits)

Commit messages must follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<optional scope>): <description>

[optional body]

[optional footer(s)]
```

### Types:
* **`feat`**: A new user-facing or system feature.
* **`fix`**: A bug fix.
* **`docs`**: Documentation only changes.
* **`refactor`**: Code changes that neither fix a bug nor add a feature.
* **`perf`**: Performance improvements.
* **`test`**: Adding or correcting tests.
* **`chore`**: Maintenance, dependency updates, build tooling.

### Examples:
```bash
feat(webhooks): add hmac signature validation for jira events
fix(engines): correct temporal validity check for deprecated decisions
test(reconstruction): add unit tests for rule HW-01 anomaly detection
```

---

## 4. Development Workflow

### Step 1: Fork and Clone
```bash
git clone https://github.com/your-username/kairo.git
cd kairo
git checkout -b feat/your-feature-name
```

### Step 2: Set Up Local Environment
```bash
# Setup backend virtual environment and dependencies
cd apps/api
uv venv .venv && source .venv/bin/activate
uv pip install -r requirements.txt

# Setup frontend dependencies
cd ../../apps/web
pnpm install
```

### Step 3: Implement Feature & Write Tests
* Ensure all new logic includes unit and integration tests.
* Maintain minimum code coverage threshold of **85%**.

### Step 4: Run Code Quality Checks
```bash
# Backend Quality Gates
cd apps/api
ruff check . --fix
ruff format .
mypy app
pytest --cov=app --cov-fail-under=85

# Frontend Quality Gates
cd ../../apps/web
pnpm lint
pnpm type-check
pnpm test
```

### Step 5: Submit Pull Request (PR)
1. Push branch to your fork.
2. Open a PR against `main` on the primary repository.
3. Fill out the PR template completely.

---

## 5. Pull Request Guidelines & Checklist

Before requesting review, ensure your PR meets the following criteria:

- [ ] **Title:** Follows Conventional Commits format.
- [ ] **Description:** Explains the *why*, *what*, and any architectural trade-offs.
- [ ] **Tests:** New tests added covering happy path, failure modes, and edge cases.
- [ ] **Coverage:** Maintained $\ge 85\%$ test coverage across modified modules.
- [ ] **Linting & Types:** Zero `ruff`, `mypy`, `eslint`, or `tsc` errors.
- [ ] **Security:** No secrets committed; complies with [SECURITY.md](file:///c:/Users/adity/OneDrive/Personal%20Vault/Desktop/Kairo/SECURITY.md).
- [ ] **Documentation:** Relevant doc files updated (`API.md`, `README.md`, etc.).

---

## 6. Review & Merge Process

1. **Automated CI Gates:** Every PR automatically triggers GitHub Actions for linting, security scans, unit tests, and integration test runs.
2. **Peer Review:** At least one core maintainer approval is required.
3. **Squash and Merge:** PRs are squash-merged into `main` with a clean commit summary.
