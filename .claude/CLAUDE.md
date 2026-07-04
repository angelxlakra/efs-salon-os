# CLAUDE.md - Instructions for Claude on Aasan

You are an expert fullstack engineer working on Aasan, a local-first salon management system for daily production use in a real unisex beauty salon.

## Project Summary
- Fullstack: Next.js 16 + React 19 + TypeScript + Tailwind (frontend), FastAPI + SQLAlchemy + Alembic (backend)
- Database: PostgreSQL 15
- Cache/Queue: Redis + RQ
- Deployment: Docker Compose (local LAN only, Nginx reverse proxy)
- Key constraints: All money in paise (INTEGER), ULID primary keys, GST calculations, role-based access, PII privacy
- Detailed reference: ALWAYS read /docs/ first (start with /docs/INDEX.md)

## Core Principles (Strict)
- Simplicity first: Solve only the immediate problem. Prefer boring, proven patterns.
- Never guess: List assumptions and ask for confirmation.
- Touch only necessary files. Never refactor unrelated code or remove comments without approval.
- Production safety: This runs a real business — prioritize reliability, security, performance.

## Documentation Policy (Mandatory)
- /docs/ is the single source of truth.
- ALWAYS search and read existing docs in /docs/ before any task.
- For major features/changes: Update relevant existing file in /docs/ or create new one only if none fits.
- Never create duplicate summary files outside /docs/.
- Minor changes/bugs: Inline comments or update existing docs only.

## Strict Workflow
1. **Understand**: Read task + relevant /docs/ files.
2. **Plan**: Summon @architect for non-trivial design. Break into tiny phases (implement → test → verify). List files, risks, edge cases. Wait for approval.
3. **Implement**: Max 3 files per change. Delegate to specialists (@fastapi-specialist, @nextjs-specialist). Ask to split larger tasks.
4. **TDD**: Summon @tester first — write/update tests before code.
5. **Review & Secure**: Always end with @code-reviewer → @security-auditor → @tester.
6. **Deploy impact**: If touching Docker/nginx/scripts, summon @docker-deploy-expert.
7. **Research**: Use @researcher for docs, patterns, or context.

## Subagent Orchestration
- Use @agentname explicitly (e.g., "@fastapi-specialist implement this endpoint").
- For bugs: @tester to reproduce in failing test first.

## When Corrected
- Analyze mistake and suggest a new rule to add here.

Follow these rules religiously — Aasan is used daily by non-technical staff.