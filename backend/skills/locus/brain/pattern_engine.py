import os
import json
import logging
from datetime import date
import asyncpg

log = logging.getLogger("brain.pattern_engine")

DATABASE_URL = os.getenv("DATABASE_URL")
NEO4J_URL = os.getenv("NEO4J_URL", "bolt://neo4j:7687")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

async def run_weekly():
    """Triggered weekly on Sunday 11PM and on-demand."""
    log.info("Running pattern engine...")
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # 5.1 DCS Trend
        dcs_rows = await conn.fetch("SELECT date, dcs FROM daily_logs WHERE checkin_type = 'morning' AND dcs IS NOT NULL ORDER BY date DESC LIMIT 14")
        dcs_values = [r['dcs'] for r in dcs_rows]
        dcs_trend = "flat"
        exhaustion_risk = False
        
        if len(dcs_values) >= 7:
            recent_avg = sum(dcs_values[:7]) / 7
            if recent_avg < 4.0:
                dcs_trend = "extended_low_capacity"
                
            # 5.5 Exhaustion Risk Predictor
            # Simplified: if avg DCS < 5 for last 5 days
            if len(dcs_values) >= 5:
                avg_5 = sum(dcs_values[:5]) / 5
                if avg_5 < 5.0:
                    # Also check task difficulty if available (simplified here)
                    exhaustion_risk = True

        # 5.2 Faction Lag Score & 5.4 Action Gap
        # Target hours: [1,2,3,4] -> [17.5, 17.5, 21.0, 14.0]
        faction_targets = {"health": 17.5, "leverage": 17.5, "craft": 21.0, "expression": 14.0}
        faction_lag = {}
        action_gap = {}
        
        # Simplified query for faction hours this week
        faction_rows = await conn.fetch("""
            SELECT faction, SUM(actual_hours) as total_hrs 
            FROM tasks 
            WHERE completed_at >= NOW() - INTERVAL '7 days' 
            GROUP BY faction
        """)
        actual_hours = {r['faction']: float(r['total_hrs'] or 0) for r in faction_rows if r['faction']}
        
        for fac, target in faction_targets.items():
            actual = actual_hours.get(fac, 0.0)
            lag = target - actual
            faction_lag[fac] = lag
            
            # Action Gap (Assuming declared priority = 8 for all as placeholder if not stored)
            declared_priority = 8 
            ag = declared_priority - (actual / target * 10) if target > 0 else 0
            action_gap[fac] = ag

        # 5.3 Deferral Patterns
        deferral_rows = await conn.fetch("SELECT task_id, COUNT(*) as cnt FROM task_deferrals GROUP BY task_id HAVING COUNT(*) >= 3")
        deferral_count = len(deferral_rows)

        # 5.6 Best Focus Windows
        # Bins: morning (6-12), afternoon (12-17), evening (17-22), night (22-6)
        # Assuming we track completion hour or time_of_day
        # For now, placeholder query
        best_focus = "morning" 

        # Write to Postgres pattern_snapshots
        await conn.execute("""
            INSERT INTO pattern_snapshots (
                snapshot_date, faction_lag_json, dcs_trend, exhaustion_risk, action_gap_json, deferral_count
            ) VALUES ($1, $2, $3, $4, $5, $6)
        """, date.today(), json.dumps(faction_lag), dcs_trend, exhaustion_risk, json.dumps(action_gap), deferral_count)
        
        # Write to Neo4j
        try:
            from neo4j import AsyncGraphDatabase
            driver = AsyncGraphDatabase.driver(NEO4J_URL, auth=("neo4j", NEO4J_PASSWORD))
            async with driver.session() as s:
                await s.run("""
                    MERGE (p:Person {name: 'Shivam'})
                    SET p.dcs_trend = $trend,
                        p.exhaustion_risk = $risk,
                        p.best_focus_window = $focus,
                        p.last_pattern_update = datetime()
                """, trend=dcs_trend, risk=exhaustion_risk, focus=best_focus)
            await driver.close()
        except Exception as e:
            log.error(f"Failed to update Neo4j with patterns: {e}")

        return {
            "dcs_trend": dcs_trend,
            "exhaustion_risk": exhaustion_risk,
            "faction_lag": faction_lag,
            "action_gap": action_gap,
            "deferral_count": deferral_count,
            "best_focus_window": best_focus
        }
    finally:
        await conn.close()
