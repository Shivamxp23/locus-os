# /opt/locus/backend/services/goal_distiller.py
# Parses Goals.md, distills Goals -> Projects -> Tasks
# Flags vague goals for clarification via Telegram

import os
import re
import json
import logging
from datetime import date, datetime
from typing import Optional
import asyncpg

log = logging.getLogger("goal-distiller")

VAULT_PATH = os.getenv("VAULT_PATH", "/vault")
GOALS_FILE = os.path.join(VAULT_PATH, "Goals.md")
DATABASE_URL = os.getenv("DATABASE_URL")

FACTION_EMOJI = {
    "health-stability": "🟢",
    "leverage-money": "🔵", 
    "craft-skills": "🟠",
    "expression-exploration": "🟣"
}


def parse_goals_file() -> list[dict]:
    """Parse Goals.md and extract structured goals."""
    if not os.path.exists(GOALS_FILE):
        return []
    
    with open(GOALS_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    
    goals = []
    current_goal = {}
    in_current = False
    
    for line in content.split("\n"):
        line = line.rstrip()
        
        # Goal header
        if line.startswith("## Goal:"):
            if current_goal:
                goals.append(current_goal)
            title = line.replace("## Goal:", "").strip()
            current_goal = {
                "title": title,
                "why": "",
                "success_criteria": [],
                "faction": "",
                "target_date": "",
                "projects": [],
                "raw": line
            }
            in_current = True
            
        elif in_current and line.startswith("### Why"):
            continue
        elif in_current and line.startswith("### Success Criteria"):
            continue
        elif in_current and line.startswith("### Faction"):
            continue
        elif in_current and line.startswith("### Target Date"):
            continue
        elif in_current and line.startswith("### Projects"):
            continue
        elif in_current and line.startswith("## Current Goals"):
            in_current = False
        elif in_current and line.startswith("## Completed Goals"):
            in_current = False
            if current_goal:
                goals.append(current_goal)
                current_goal = {}
        elif in_current:
            if line.startswith("- "):
                if current_goal.get("success_criteria") is not None:
                    current_goal["success_criteria"].append(line[2:].strip())
            elif line.startswith("- ") and "projects" in str(current_goal):
                current_goal["projects"].append(line[2:].strip())
            elif current_goal.get("why") is not None:
                if current_goal["why"]:
                    current_goal["why"] += " " + line.strip()
                else:
                    current_goal["why"] = line.strip()
    
    if current_goal:
        goals.append(current_goal)
    
    return goals


def is_vague(goal: dict) -> list[str]:
    """Check if a goal is too vague. Returns list of issues."""
    issues = []
    
    title = goal.get("title", "")
    if not title or len(title) < 10:
        issues.append("Goal title is empty or too short")
    
    why = goal.get("why", "")
    if not why or len(why) < 20:
        issues.append("'Why' section is missing or too brief")
    
    criteria = goal.get("success_criteria", [])
    if not criteria:
        issues.append("No success criteria defined")
    else:
        # Check if criteria are measurable
        for c in criteria:
            c_lower = c.lower()
            if not any(w in c_lower for w in ["%","by", "number", "times", "hours", "days", "achieve", "complete"]):
                issues.append(f"Criteria '{c}' is not measurable")
                break
    
    faction = goal.get("faction", "")
    if not faction:
        issues.append("No faction specified")
    
    target = goal.get("target_date", "")
    if not target:
        issues.append("No target date set")
    
    return issues


def distill_goals() -> dict:
    """Main function: Parse goals, check vagueness, generate projects/tasks."""
    goals = parse_goals_file()
    
    result = {
        "parsed_at": datetime.now().isoformat(),
        "goals": [],
        "vague_goals": [],
        "projects": [],
        "tasks": []
    }
    
    for goal in goals:
        issues = is_vague(goal)
        
        goal_entry = {
            "title": goal.get("title", ""),
            "faction": goal.get("faction", ""),
            "target_date": goal.get("target_date", ""),
            "is_vague": len(issues) > 0,
            "vagueness_issues": issues if issues else None
        }
        
        result["goals"].append(goal_entry)
        
        if issues:
            result["vague_goals"].append(goal_entry)
        else:
            # Generate projects from goal
            projects = goal.get("projects", [])
            for proj in projects:
                result["projects"].append({
                    "goal": goal.get("title", ""),
                    "project": proj,
                    "faction": goal.get("faction", "")
                })
    
    log.info(f"Distilled {len(goals)} goals: {len(result['vague_goals'])} vague, {len(result['projects'])} projects")
    return result


async def sync_to_database(distilled: dict) -> bool:
    """Sync distilled goals to Postgres tables."""
    if not DATABASE_URL:
        log.warning("No DATABASE_URL")
        return False
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        for goal in distilled.get("goals", []):
            # Insert into projects table
            if not goal.get("is_vague"):
                # This goal is ready - add as project
                title = goal.get("title", "")
                faction = goal.get("faction", "")
                
                if title and faction:
                    await conn.execute("""
                        INSERT INTO projects (title, faction, status)
                        VALUES ($1, $2, 'active')
                        ON CONFLICT DO NOTHING
                    """, title, faction)
        
        # Log vague goals for followup
        for goal in distilled.get("vague_goals", []):
            await conn.execute("""
                INSERT INTO behavioral_events (user_id, event_type, data)
                VALUES ($1, $2, $3)
            """, "shivam", "vague_goal", json.dumps(goal))
        
        await conn.close()
        log.info(f"Synced {len(distilled['goals'])} goals to DB")
        return True
    except Exception as e:
        log.error(f"Failed to sync goals: {e}")
        return False


def format_for_display(distilled: dict) -> str:
    """Format distilled goals for display."""
    lines = ["# Goal Distillation\n"]
    
    if not distilled.get("goals"):
        lines.append("No goals found in Goals.md")
        return "\n".join(lines)
    
    # Clear goals
    clear = [g for g in distilled["goals"] if not g.get("is_vague")]
    vague = [g for g in distilled["goals"] if g.get("is_vague")]
    
    if clear:
        lines.append(f"## Ready ({len(clear)})")
        for g in clear:
            e = FACTION_EMOJI.get(g.get("faction", ""), "⚪")
            lines.append(f"{e} {g['title']}")
            if g.get("target_date"):
                lines.append(f"   Due: {g['target_date']}")
            lines.append("")
    
    if vague:
        lines.append(f"## Needs Clarification ({len(vague)})")
        for g in vague:
            lines.append(f"⚠️ {g['title']}")
            for issue in g.get("vagueness_issues", []):
                lines.append(f"   - {issue}")
            lines.append("")
    
    return "\n".join(lines)


def get_clarification_prompt(goal: dict) -> str:
    """Generate a clarification question for a vague goal."""
    issues = goal.get("vagueness_issues", [])
    
    questions = []
    
    if any("title" in i.lower() for i in issues):
        questions.append("Can you rephrase your goal in one specific sentence?")
    
    if any("why" in i.lower() for i in issues):
        questions.append("Why does this goal matter to you? What's the deeper reason?")
    
    if any("criteria" in i.lower() for i in issues):
        questions.append("How will you know you've succeeded? Give me a specific measure.")
    
    if any("faction" in i.lower() for i in issues):
        questions.append("Which faction does this belong to? health-stability, leverage-money, craft-skills, or expression-exploration?")
    
    if any("target" in i.lower() for i in issues):
        questions.append("When do you want to achieve this by?")
    
    if not questions:
        return f"Let's clarify: {goal.get('title', 'this goal')}"
    
    return "\n".join(questions)