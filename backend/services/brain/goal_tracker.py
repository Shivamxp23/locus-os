import os
import json
import logging
from datetime import date
import asyncpg

log = logging.getLogger("brain.goal_tracker")
DATABASE_URL = os.getenv("DATABASE_URL")
VAULT_PATH = os.getenv("VAULT_PATH", "/vault")

async def run_weekly_review() -> dict:
    log.info("Running weekly goal tracker review...")
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # 1. Dead Node Detection
        dead_node_rows = await conn.fetch("SELECT id FROM projects WHERE last_activity_at < NOW() - INTERVAL '60 days' AND status = 'active'")
        dead_nodes = [str(r['id']) for r in dead_node_rows]
        if dead_nodes:
            await conn.execute("UPDATE projects SET status = 'dead_node' WHERE id = ANY($1::uuid[])", dead_node_rows)
            
        # 2. Active Project Cap
        active_counts = await conn.fetch("SELECT faction, COUNT(*) as cnt FROM projects WHERE status = 'active' GROUP BY faction")
        project_overload = [r['faction'] for r in active_counts if r['cnt'] > 3]
        
        # 3. Action Gap (Placeholder data for now, requires deeper tracking of intended priority vs actual)
        action_gaps = {"1": 0.0, "2": 0.0, "3": 0.0, "4": 0.0}
        faction_hours = {"1": 0.0, "2": 0.0, "3": 0.0, "4": 0.0}
        faction_lag = {"1": 0.0, "2": 0.0, "3": 0.0, "4": 0.0}
        momentum_scores = {"1": 0.0, "2": 0.0, "3": 0.0, "4": 0.0}
        
        # 4. Completion Rate per Project
        # CR = tasks_completed / tasks_total * 100
        # Projects with CR < 20% and age > 30 days -> flag stalled
        stalled_projects = []
        project_stats = await conn.fetch("""
            SELECT p.id, 
                   COUNT(t.id) as total_tasks, 
                   SUM(CASE WHEN t.status = 'done' THEN 1 ELSE 0 END) as done_tasks,
                   EXTRACT(DAY FROM NOW() - p.created_at) as age_days
            FROM projects p
            LEFT JOIN tasks t ON t.parent_project_id = p.id
            WHERE p.status = 'active'
            GROUP BY p.id, p.created_at
        """)
        for r in project_stats:
            total = r['total_tasks']
            done = r['done_tasks']
            if total > 0 and r['age_days'] > 30:
                cr = (done / total) * 100
                if cr < 20:
                    stalled_projects.append(str(r['id']))
                    
        # 5. Deferral Pattern Summary
        deferral_rows = await conn.fetch("SELECT task_id FROM task_deferrals GROUP BY task_id HAVING COUNT(*) >= 3")
        deferral_patterns = [str(r['task_id']) for r in deferral_rows]
        
        # Compute average DCS this week
        dcs_row = await conn.fetchrow("SELECT AVG(dcs) as avg_dcs FROM daily_logs WHERE date >= NOW() - INTERVAL '7 days' AND checkin_type = 'morning'")
        dcs_avg = float(dcs_row['avg_dcs'] or 0.0)
        
        review_json = {
            "week_ending": str(date.today()),
            "faction_hours": faction_hours,
            "faction_lag": faction_lag,
            "action_gaps": action_gaps,
            "dead_nodes": dead_nodes,
            "stalled_projects": stalled_projects,
            "deferral_patterns": deferral_patterns,
            "dcs_avg_this_week": dcs_avg,
            "momentum_scores": momentum_scores,
            "project_overload_factions": project_overload
        }
        
        # Write to Obsidian note
        note_content = f"# Weekly Review - {date.today()}\n\n"
        note_content += f"**Average DCS this week:** {dcs_avg:.2f}\n\n"
        note_content += f"## Dead Nodes\n{', '.join(dead_nodes) if dead_nodes else 'None'}\n\n"
        note_content += f"## Stalled Projects\n{', '.join(stalled_projects) if stalled_projects else 'None'}\n\n"
        note_content += f"## Deferred Tasks (3+ times)\n{', '.join(deferral_patterns) if deferral_patterns else 'None'}\n\n"
        note_content += f"## Project Overload\n{', '.join(project_overload) if project_overload else 'None'}\n"
        
        obsidian_dir = os.path.join(VAULT_PATH, "05-Content", "WeeklyReview")
        os.makedirs(obsidian_dir, exist_ok=True)
        note_path = os.path.join(obsidian_dir, f"{date.today()}.md")
        
        with open(note_path, "w", encoding="utf-8") as f:
            f.write(note_content)
            
        # Write to Postgres
        await conn.execute("""
            INSERT INTO weekly_reviews (week_ending, review_json, obsidian_note_path)
            VALUES ($1, $2, $3)
        """, date.today(), json.dumps(review_json), note_path)
        
        return review_json
    finally:
        await conn.close()
