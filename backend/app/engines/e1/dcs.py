"""
DCS (Daily Capacity Score) Calculation Engine.
Pure function — no side effects, fully testable.

Formula: DCS = ((E + M + S) / 3) × (1 − ST/20)

Modes:
  SURVIVAL:   0.0 – 2.0
  RECOVERY:   2.1 – 4.0
  NORMAL:     4.1 – 6.0
  DEEP_WORK:  6.1 – 8.0
  PEAK:       8.1 – 10.0
"""

from dataclasses import dataclass
from enum import Enum


class Mode(Enum):
    SURVIVAL = "SURVIVAL"
    RECOVERY = "RECOVERY"
    NORMAL = "NORMAL"
    DEEP_WORK = "DEEP_WORK"
    PEAK = "PEAK"


@dataclass
class DCSResult:
    score: float
    mode: Mode
    mode_description: str
    recommended_task_types: list[str]


def calculate_dcs(energy: int, mood: int, sleep: int, stress: int) -> DCSResult:
    """
    Calculate Daily Capacity Score from morning metrics.

    Args:
        energy: Energy level 1-10
        mood: Mood level 1-10
        sleep: Sleep quality 1-10
        stress: Stress level 1-10

    Returns:
        DCSResult with score, mode, description, and task recommendations.

    Raises:
        ValueError: If any metric is out of range.
    """
    for name, val in [
        ("energy", energy),
        ("mood", mood),
        ("sleep", sleep),
        ("stress", stress),
    ]:
        if not 1 <= val <= 10:
            raise ValueError(f"{name} must be between 1 and 10, got {val}")

    score = ((energy + mood + sleep) / 3) * (1 - stress / 20)
    score = round(score, 2)

    if score <= 2.0:
        mode = Mode.SURVIVAL
        description = "You are not okay. Protect the non-negotiables. That's it."
        tasks = ["Non-negotiables only: eat, sleep, maintain academic deadlines"]
    elif score <= 4.0:
        mode = Mode.RECOVERY
        description = "Below baseline. Gentle movement only. No hard pushes."
        tasks = [
            "Difficulty ≤ 4 tasks only",
            "Prefer Expression/Explore activities",
            "Maximum 2 non-essential tasks",
        ]
    elif score <= 6.0:
        mode = Mode.NORMAL
        description = "Standard operating. A full, balanced day is possible."
        tasks = [
            "Difficulty ≤ 7 allowed",
            "Balance across at least 2 factions",
            "3-4 tasks outside non-negotiables",
        ]
    elif score <= 8.0:
        mode = Mode.DEEP_WORK
        description = "You are sharp. Use this for your hardest, highest-value work."
        tasks = [
            "Schedule highest TWS tasks in 2-3 hour uninterrupted block",
            "Difficulty ≤ 9 allowed",
            "4-5 tasks outside non-negotiables",
        ]
    else:
        mode = Mode.PEAK
        description = "Rare. Pull out your most ambitious tasks. Do not waste this."
        tasks = [
            "All difficulty levels available",
            "Tackle your single most ambitious task first",
            "5-6 tasks possible",
        ]

    return DCSResult(
        score=score,
        mode=mode,
        mode_description=description,
        recommended_task_types=tasks,
    )
