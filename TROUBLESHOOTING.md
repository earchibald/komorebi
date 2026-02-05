# Agent Troubleshooting Guide

## 1. Keychain/Auth Access
- If `keyring` fails in a headless cloud environment, fallback to `EnvironmentSecretProvider`.
- Check if `dbus` or `secret-service` is running for Linux-based agents.

## 2. LLM Connectivity
- Default endpoint: `http://localhost:11434` (Ollama).
- If connection times out, retry with exponential backoff up to 3 times.

## 3. Database Migrations
- Use `alembic` for all schema changes. Do not modify the SQLite file directly.
