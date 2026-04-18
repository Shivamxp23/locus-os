# /opt/locus/backend/services/scheduler_engine.py
# Pure scheduling logic — no I/O, no DB calls.
# This is the brain of Engine 3: the Scheduling Engine.
#
# Algorithm (from LOCUS_SYSTEM_v1.md §7 + LOCUS_ARCHITECTURE_v4.md §10):
#   1. Read DCS + mode → set difficulty ceiling
#   2. Filter pending tasks by difficulty ≤ ceiling
#   3. Calculate faction lag scores (target - actual this week)
#   4. Apply lag bonus to TWS: adjusted_tws = tws + (lag * 0.3)
#   5. Apply deferral penalty: adjusted_tws += (deferral_count * 0.5)
#   6. Sort by adjusted_tws DESC
#   7. Select tasks until 80% of available time filled
#   8. Faction balance check — no more than 60% from one faction
#   9. Return ordered schedule with time estimates

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TaskItem:
    id: str
    title: str
    faction: str
    priority: int
    urgency: int
    difficulty: int
    tws: float
    estimated_hours: float = 1.0
    deferral_count: int = 0
    scheduled_date: Optional[str] = None
    adjusted_tws: float = 0.0


@dataclass
class FactionHealth:
    faction: str
    target_hours: float
    actual_hours: float
    lag: float = 0.0       # target - actual (positive = behind)
    momentum: float = 0.0  # completion rate trend


@dataclass
class ScheduleConfig:
    dcs: float = 5.0
    mode: str = "NORMAL"
    available_hours: float = 8.0
    buffer_ratio: float = 0.8       # Only schedule 80% of available time
    max_faction_ratio: float = 0.6  # No faction gets more than 60%
    lag_weight: float = 0.3         # How much faction lag boosts TWS
    deferral_bonus: float = 0.5     # Extra TWS per deferral


@dataclass
class ScheduleResult:
    tasks: list = field(default_factory=list)
    mode: str = "NORMAL"
    dcs: float = 5.0
    total_hours: float = 0.0
    available_hours: float = 0.0
    faction_breakdown: dict = field(default_factory=dict)
    message: str = ""


# ── Mode → difficulty ceiling ──
MODE_DIFFICULTY_CEILING = {
    "SURVIVAL":  0,   # No productive tasks
    "RECOVERY":  4,   # Gentle only
    "NORMAL":    7,   # Standard
    "DEEP_WORK": 9,   # Push hard
    "PEAK":      10,  # Everything unlocked
}

# ── Default faction targets (hours/week) ──
DEFAULT_FACTION_TARGETS = {
    "health":     17.5,
    "leverage":   20.0,
    "craft":      15.0,
    "expression":  7.5,
}

FACTION_EMOJI = {
    "health": "🟢",
    "leverage": "🔵",
    "craft": "🟠",
    "expression": "🟣",
}


def generate_schedule(
    tasks: list[TaskItem],
    faction_health: list[FactionHealth],
    config: ScheduleConfig
) -> ScheduleResult:
    """
    Main scheduling algorithm.
    
    Args:
        tasks: All pending tasks
        faction_health: Current faction health data for this week
        config: Schedule configuration (DCS, mode, available time)
    
    Returns:
        ScheduleResult with ordered task list and metadata
    """
    result = ScheduleResult(
        mode=config.mode,
        dcs=config.dcs,
        available_hours=config.available_hours,
    )

    # ── Step 1: SURVIVAL mode = no tasks ──
    if config.mode == "SURVIVAL":
        result.message = (
            "🔴 SURVIVAL mode (DCS ≤ 2). Protect non-negotiables only.\n"
            "No productive tasks scheduled. Focus on rest, food, basic hygiene.\n"
            "Tomorrow will be better."
        )
        return result

    # ── Step 2: Filter by difficulty ceiling ──
    ceiling = MODE_DIFFICULTY_CEILING.get(config.mode, 7)
    eligible = [t for t in tasks if t.difficulty <= ceiling]

    if not eligible:
        result.message = f"No tasks within difficulty ≤ {ceiling} for {config.mode} mode."
        return result

    # ── Step 3: Build faction lag map ──
    lag_map = {}
    for fh in faction_health:
        fh.lag = max(0, fh.target_hours - fh.actual_hours)
        lag_map[fh.faction] = fh.lag

    # ── Step 4: Calculate adjusted TWS ──
    for t in eligible:
        faction_lag = lag_map.get(t.faction, 0)
        t.adjusted_tws = (
            t.tws
            + (faction_lag * config.lag_weight)       # Boost under-served factions
            + (t.deferral_count * config.deferral_bonus)  # Prioritize deferred tasks
        )

    # ── Step 5: Sort by adjusted TWS ──
    eligible.sort(key=lambda t: t.adjusted_tws, reverse=True)

    # ── Step 6: Select tasks until 80% of time filled ──
    max_hours = config.available_hours * config.buffer_ratio
    scheduled_hours = 0.0
    faction_hours: dict[str, float] = {"health": 0, "leverage": 0, "craft": 0, "expression": 0}
    scheduled_tasks = []

    for t in eligible:
        if scheduled_hours + t.estimated_hours > max_hours:
            continue

        # ── Step 7: Faction balance check ──
        faction_total = faction_hours.get(t.faction, 0) + t.estimated_hours
        if scheduled_hours > 0:
            faction_ratio = faction_total / (scheduled_hours + t.estimated_hours)
            if faction_ratio > config.max_faction_ratio and len(scheduled_tasks) > 2:
                continue  # Skip — this faction is over-represented

        scheduled_tasks.append(t)
        scheduled_hours += t.estimated_hours
        faction_hours[t.faction] = faction_hours.get(t.faction, 0) + t.estimated_hours

    result.tasks = scheduled_tasks
    result.total_hours = round(scheduled_hours, 1)
    result.faction_breakdown = {k: round(v, 1) for k, v in faction_hours.items() if v > 0}

    # ── Step 8: Build summary message ──
    if scheduled_tasks:
        mode_emoji = {"RECOVERY": "🟡", "NORMAL": "⚪", "DEEP_WORK": "🔵", "PEAK": "🟣"}.get(config.mode, "⚪")
        lines = [f"{mode_emoji} **{config.mode}** (DCS: {config.dcs}) — {result.total_hours}h scheduled\n"]
        
        for i, t in enumerate(scheduled_tasks, 1):
            emoji = FACTION_EMOJI.get(t.faction, "⚪")
            defer_flag = f" ⚠️×{t.deferral_count}" if t.deferral_count >= 2 else ""
            lines.append(
                f"{i}. {emoji} {t.title} ({t.estimated_hours}h, D:{t.difficulty}){defer_flag}"
            )

        if result.faction_breakdown:
            lines.append(f"\n📊 Faction split: " + " | ".join(
                f"{FACTION_EMOJI.get(f, '')}{f[:3]}:{h}h" for f, h in result.faction_breakdown.items()
            ))

        result.message = "\n".join(lines)
    else:
        result.message = "No tasks could be scheduled within the constraints."

    return result
