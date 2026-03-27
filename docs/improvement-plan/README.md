# Improvement Plan — TPS Cita Check

**Created:** 2026-03-27
**Last updated:** 2026-03-27
**Status:** Planning

## Overview

This directory contains the full codebase improvement plan derived from a comprehensive analysis of all source files in the TPS Cita Check project. The analysis covers code quality, security, reliability, performance, testability, maintainability, and operational concerns.

## Document Index

| File | Description |
|------|-------------|
| [ANALYSIS.md](ANALYSIS.md) | Full codebase analysis — all findings with file/line citations, explanations, and priorities |
| [PROGRESS.md](PROGRESS.md) | Master progress tracker — status of every issue across all sprints |
| [SPRINT-1-quick-wins.md](SPRINT-1-quick-wins.md) | Sprint 1: Security quick-wins and low-effort fixes (~1-2 hours) |
| [SPRINT-2-refactoring.md](SPRINT-2-refactoring.md) | Sprint 2: Code deduplication and structural refactoring (~half day) |
| [SPRINT-3-test-coverage.md](SPRINT-3-test-coverage.md) | Sprint 3: Test coverage expansion (~half-to-full day) |
| [SPRINT-4-operational.md](SPRINT-4-operational.md) | Sprint 4: Operational hardening (~half day) |

## How to use

1. Start with **ANALYSIS.md** for full context on every finding
2. Check **PROGRESS.md** for current status at a glance
3. Open the relevant **SPRINT-N** file when starting implementation work
4. Update status checkboxes in both the sprint file and PROGRESS.md as you go

## Priority legend

| Priority | Meaning |
|----------|---------|
| **Critical** | Security risk or data loss — fix immediately |
| **High** | Significant impact on reliability or maintainability — fix this sprint |
| **Medium** | Quality improvement — fix when working in the area |
| **Low** | Nice-to-have cleanup — fix opportunistically |

## Effort legend

| Effort | Meaning |
|--------|---------|
| **S** | Small — a few lines, <30 minutes |
| **M** | Medium — a focused session, 1-3 hours |
| **L** | Large — multiple sessions, half day+ |
