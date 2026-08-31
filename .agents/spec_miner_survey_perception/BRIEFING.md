# BRIEFING — 2026-08-30T20:11:00Z

## Mission
Perform comprehensive specification mining and technical survey for Entity Perception & Battlefield Memory Invariants (R2) in VEMINS ESP.

## 🔒 My Identity
- Archetype: Specification Miner
- Roles: Specification Miner, Teamwork specialist
- Working directory: /data/data/com.termux/files/home/veminsEsp/.agents/spec_miner_survey_perception/
- Original parent: 5580e2a8-b30f-49b5-8218-bc08637dfba1
- Milestone: Perception & Invariants Spec Survey (R2)

## 🔒 Key Constraints
- Read-only miner: Do NOT implement anything.
- Probe all discovered features and invariants completely.
- Structure findings with exact memory chains, offsets, data structures, field mappings, coordinate conversions, filtering, and edge cases.
- Produce handoff.md following 5-component protocol.

## Current Parent
- Conversation ID: 5580e2a8-b30f-49b5-8218-bc08637dfba1
- Updated: 2026-08-30T20:11:00Z

## Task Summary
- **What to build**: Specification report on Entity Perception & Battlefield Memory Invariants.
- **Success criteria**: Comprehensive documentation of memory chain invariants, entity parsing, coordinate continuity, camera tracking, dictionary hole handling, gate bypass, struct definitions, packing, and projection math.
- **Interface contracts**: `offsets.json`, `FIELD_MAP.md`, `ARCHITECTURE.md`, `perception/schema.py`, `class_enum.py`, `minimap_projection.py`, `vemins_daemon.c`.
- **Code layout**: Documentation in handoff.md.

## Key Decisions Made
- Analyze all canonical files in the repository to extract ground truth invariants and cross-reference discrepancies.

## Artifact Index
- `.agents/spec_miner_survey_perception/handoff.md` — Final comprehensive spec mining report.
- `.agents/spec_miner_survey_perception/progress.md` — Agent heartbeat and progress tracking.
