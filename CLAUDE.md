# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status

This repository currently contains only a project plan (`docs/sb-bookclub-app-plan.md`) — no application code, dependency manifests, or config exist yet. There are no build, lint, or test commands to run until the project is scaffolded. When starting implementation, follow the tech stack and phased task breakdown below rather than introducing a different stack.

## Project Overview

Book Club Tracker: a web app for a 4-person book club to track books read, log individual ratings/comments, and browse reading history. Each member has their own login; data is shared/stored online across devices.

## Planned Tech Stack

- **Framework**: Flask (app factory pattern)
- **Database**: SQLite to start (or Postgres via Supabase/Neon if hosting requires it — watch for hosts with ephemeral disks if using SQLite)
- **ORM**: SQLAlchemy via Flask-SQLAlchemy
- **Migrations**: Flask-Migrate
- **Auth**: Flask-Login + Werkzeug's built-in password hashing. 4 member accounts are manually seeded — no self-registration flow.
- **Forms**: Flask-WTF (validation + CSRF protection)
- **Frontend**: Server-rendered Jinja2 templates + Tailwind CSS (CDN) or plain CSS — no separate frontend framework
- **Hosting**: Render or Railway
- **Book metadata (optional)**: Open Library API for auto-filling cover/author

## Planned Data Model

- **Member**: id, username, password_hash, display_name
- **Book**: id, title, author, cover_url, genre, date_added, added_by (FK → Member), status (to-read / currently reading / finished / abandoned)
- **Rating**: id, book_id (FK → Book), member_id (FK → Member), score, comment, date_rated
- **Meeting** *(optional, later)*: id, book_id (FK → Book), date, notes

A member can only edit/delete their own rating. Book detail views should show all 4 members' ratings side by side plus the average.

## Key Open Decisions

See `docs/sb-bookclub-app-plan.md` for full context. Resolve these consistently rather than re-deciding ad hoc:

1. Can anyone edit any book's metadata, or only the person who added it? *(suggested: anyone, keep it simple)*
2. Can a member delete their own rating, or only edit it?
3. Rating scale (1–5, 1–10, half-star increments) — decide before building Ratings, since it affects both schema and UI.
4. SQLite vs. Postgres — SQLite needs a host with persistent disk.

## Development Approach

This is an educational project. `docs/sb-bookclub-app-plan.md` is a phased checklist (Setup → Auth → Core CRUD → Views & Polish → Nice-to-Haves), not a full implementation spec — work through phases in order, researching unfamiliar pieces (Flask-Login, SQLAlchemy relationships, etc.) as they come up rather than upfront.
