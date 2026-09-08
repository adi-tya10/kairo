# KAIRO: Cryptography, Secrets Management & Key Hygiene

> **Domain:** Security, Privacy & Compliance  
> **Document ID:** KAIRO-SEC-CRYPTO  
> **Standard:** AES-256-GCM & TLS 1.3 Strict

---

## 1. Secrets & Token Storage

* **OAuth Tokens at Rest:** Third-party OAuth tokens and secrets stored in `integrations.encrypted_credentials` are encrypted using **AES-256-GCM** with a rotating master key.
* **In-Transit Communication:** All external and internal HTTP traffic requires **TLS 1.3** (TLS 1.2 fallback).

---

## 2. Secrets Management Runbook

* **Zero Commits:** `.env` files are permanently ignored in `.gitignore`.
* **Automated Scanners:** CI/CD enforces automated pre-commit secret scans (TruffleHog / GitGuardian).
* **Key Rotation:** Master encryption keys rotate every 90 days with automated zero-downtime re-encryption scripts.
