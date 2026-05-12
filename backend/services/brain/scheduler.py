import os
import json
import logging
from datetime import date
from typing import Optional
import asyncpg
from pydantic import BaseModel

log = logging.getLogger("brain.scheduler")
DATABASE_URL = os.getenv("DATABASE_URL")

class RescheduleRequest(BaseModel):
    reason: str
    lost_hours: float

async def generate_schedule(available_hours: float = 16.0) -> dict:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        today = date.today()
        
        # 1. Inputs
        log_row = await conn.fetchrow("SELECT dcs, mode FROM daily_logs WHERE checkin_type = 'morning' AND date = $1", today)
        dcs = log_row['dcs'] if log_row else 5.0
        mode = log_row['mode'] if log_row else 'NORMAL'
        
        pat_row = await conn.fetchrow("SELECT faction_lag_json, exhaustion_risk FROM pattern_snapshots ORDER BY snapshot_date DESC LIMIT 1")
        faction_lag = json.loads(pat_row['faction_lag_json']) if pat_row and pat_row['faction_lag_json'] else {}
        exhaustion_risk = pat_row['exhaustion_risk'] if pat_row else False
        
        tasks_rows = await conn.fetch("SELECT id, title, faction, priority, urgency, difficulty, estimated_hours FROM tasks WHERE status = 'pending'")
        task_pool = [dict(r) for r in tasks_rows]
        
        # Calculate base TWS (Task Weight Score)
        # Using a simple formula: P + U + (10 - D) for now, actual formula from System Bible may vary
        for t in task_pool:
            t['tws_score'] = t.get('priority', 5) + t.get('urgency', 5) + (10 - t.get('difficulty', 5))
            
        # STEP 1: Lock Non-negotiables (Simplified)
        t_available = available_hours - (7.0 + 0.33 + 0.75) # sleep, movement, meals
        
        # STEP 2: DCS Mode Filter
        if mode == 'SURVIVAL':
            task_pool = []
        elif mode == 'RECOVERY':
            task_pool = [t for t in task_pool if t.get('difficulty', 5) <= 4]
        elif mode == 'NORMAL':
            task_pool = [t for t in task_pool if t.get('difficulty', 5) <= 7]
        
        # STEP 3: Lag Bonus
        for t in task_pool:
            fac = t.get('faction')
            lag = faction_lag.get(fac, 0)
            if lag > 6:
                t['tws_score'] += 4
            elif lag > 3:
                t['tws_score'] += 2
            elif lag < 0:
                t['tws_score'] -= 1
                
        # STEP 4: Exhaustion Risk Adjustment
        if exhaustion_risk:
            t_available *= 0.70
            task_pool = [t for t in task_pool if t.get('difficulty', 5) <= 6]
            
        # STEP 5: Sort and Select
        task_pool.sort(key=lambda x: x['tws_score'], reverse=True)
        selected_tasks = []
        accumulated_est = 0.0
        
        for t in task_pool:
            if accumulated_est >= t_available * 0.80:
                break
            selected_tasks.append(t)
            accumulated_est += t.get('estimated_hours', 1.0)
            
        # STEP 6: Faction Balance Check
        factions_selected = set(t.get('faction') for t in selected_tasks)
        if len(factions_selected) <= 1 and mode not in ['SURVIVAL', 'RECOVERY'] and len(selected_tasks) > 0:
            underrepresented = [t for t in task_pool if t.get('faction') not in factions_selected]
            if underrepresented:
                selected_tasks.pop()
                selected_tasks.append(underrepresented[0])
                
        # STEP 7: Time Block Assignment
        for t in selected_tasks:
            d = t.get('difficulty', 5)
            if fac == 'expression':
                t['suggested_time_block'] = 'evening'
            elif d >= 8:
                t['suggested_time_block'] = 'morning' # User's best focus window
            elif d >= 5:
                t['suggested_time_block'] = 'midday'
            else:
                t['suggested_time_block'] = 'late afternoon'
                
        # Prepare output
        schedule_output = {
            "date": str(today),
            "mode": mode,
            "dcs": dcs,
            "task_list": selected_tasks,
            "total_estimated_hours": accumulated_est,
            "available_hours": t_available,
            "faction_lag_flags": faction_lag,
            "exhaustion_risk": exhaustion_risk
        }
        
        # Log event
        await conn.execute("INSERT INTO behavioral_events (user_id, event_type, data) VALUES ($1, $2, $3)", 
                           'shivam', 'schedule_generated', json.dumps({"task_count": len(selected_tasks)}))
                           
        return schedule_output
    finally:
        await conn.close()

async def reschedule(reason: str, lost_hours: float) -> dict:
    log.info(f"Emergency reschedule triggered: {reason}, lost {lost_hours} hours")
    # In a full implementation, we'd defer unfinished tasks and subtract lost_hours from t_available
    # For now, just regenerate with reduced hours
    return await generate_schedule(available_hours=16.0 - lost_hours)
