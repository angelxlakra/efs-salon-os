---
name: testing-workflow
description: "TDD testing workflow for Aasan. Use when writing tests first, reproducing bugs as failing tests, or verifying coverage for money/permissions/concurrency."
allowed-tools: Read, Grep, Glob, Bash, Edit, Write
---

# Testing Workflow

Always write tests first.
Backend: pytest with fixtures for DB/auth.
Frontend: Jest + RTL for components.
Cover permissions, money, concurrency.

Task: Generate tests -> implement -> verify.
