---
description: Automatically scans sprint plans and recent daily logs to generate prioritized daily tasks whenever asked.
globs: "*"
---

# SolarSense EMS — Daily Standup & Task Kickoff Rule

Whenever the user asks questions such as:
- *"What are my today's tasks?"*
- *"What should I do today?"*
- *"Daily standup / daily kickoff"*
- *"What's next on our plan?"*

You MUST follow this exact 4-step autonomous audit protocol before presenting today's agenda:

## Step 1: Scan Master Sprint Plans
Read and parse the current active sprint plans:
- `docs/week4_implementation_plan_abubakar_zaeem.md` (or the latest week plan in `docs/`)
- `docs/WEEK_4_5_SPRINT_PLAN_AND_AUDIT.md`

## Step 2: Audit Actual Execution (Last 1–2 Days)
Inspect real git metadata and daily engineering logs:
- Read the latest 1–2 daily logs in `docs/daily_logs/` (e.g., `YYYY-MM-DD.md`)
- Run `git log -n 8 --oneline` to see the latest commits merged by both **Abubakar** and **Zaeem**

## Step 3: Cross-Reference & Delta Analysis
Identify the delta between what was planned and what has actually landed in the codebase:
1. **Delivered & Verified:** Code already implemented with passing unit tests.
2. **Carried Over / In Progress:** Partially implemented tasks or missing tests/docs.
3. **Zaeem's Track:** Progress on Computer Vision, Defect Classification, and Load EDA.

## Step 4: Output the Daily Executive Briefing
Format the response using this standard structure:
1. **🚀 Yesterday's Accomplishments (Verified):** Brief bullet points with commit hashes and file links.
2. **🎯 Abubakar's Priority Deliverables for Today (Lead):** Exactly 2–3 concrete, high-impact tasks with target file paths, expected test coverage, and physics/engineering constraints.
3. **🤝 Zaeem's Parallel Track & Sync Points:** Dependencies or interfaces to align with Zaeem.
4. **⚡ Immediate Next Step:** The exact first command or file to open to start working right now.
