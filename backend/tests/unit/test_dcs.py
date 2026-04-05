"""Unit tests for DCS (Daily Capacity Score) calculation engine."""

import pytest
from app.engines.e1.dcs import calculate_dcs, Mode, DCSResult


class TestDCSCalculation:
    """Test the DCS formula: ((E + M + S) / 3) × (1 − ST/20)"""

    def test_dcs_basic_calculation(self):
        """Test the example from the spec: E=6, M=7, S=5, ST=4 → DCS=4.8"""
        result = calculate_dcs(energy=6, mood=7, sleep=5, stress=4)
        assert result.score == 4.8
        assert result.mode == Mode.NORMAL

    def test_dcs_perfect_score(self):
        """E=10, M=10, S=10, ST=1 → DCS should be near 10"""
        result = calculate_dcs(10, 10, 10, 1)
        expected = ((10 + 10 + 10) / 3) * (1 - 1 / 20)
        assert abs(result.score - expected) < 0.01
        assert result.mode == Mode.PEAK

    def test_dcs_worst_score(self):
        """E=1, M=1, S=1, ST=10 → DCS should be near 0.5"""
        result = calculate_dcs(1, 1, 1, 10)
        expected = ((1 + 1 + 1) / 3) * (1 - 10 / 20)
        assert abs(result.score - expected) < 0.01
        assert result.mode == Mode.SURVIVAL

    def test_dcs_zero_stress(self):
        """E=5, M=5, S=5, ST=0 → DCS = 5.0 (stress at minimum)"""
        result = calculate_dcs(5, 5, 5, 1)
        expected = ((5 + 5 + 5) / 3) * (1 - 1 / 20)
        assert abs(result.score - expected) < 0.01


class TestDCSModes:
    """Test all 5 operating modes with boundary values."""

    def test_survival_mode(self):
        """DCS 0.0–2.0 → SURVIVAL"""
        result = calculate_dcs(1, 1, 1, 10)
        assert result.mode == Mode.SURVIVAL
        assert result.score <= 2.0

    def test_survival_boundary(self):
        """DCS exactly 2.0 should be SURVIVAL"""
        result = calculate_dcs(2, 2, 2, 6)
        assert result.score <= 2.0
        assert result.mode == Mode.SURVIVAL

    def test_recovery_mode(self):
        """DCS 2.1–4.0 → RECOVERY"""
        result = calculate_dcs(3, 3, 3, 5)
        assert result.mode == Mode.RECOVERY
        assert 2.1 <= result.score <= 4.0

    def test_normal_mode(self):
        """DCS 4.1–6.0 → NORMAL"""
        result = calculate_dcs(6, 7, 5, 4)
        assert result.mode == Mode.NORMAL
        assert 4.1 <= result.score <= 6.0

    def test_deep_work_mode(self):
        """DCS 6.1–8.0 → DEEP_WORK"""
        result = calculate_dcs(8, 8, 7, 3)
        assert result.mode == Mode.DEEP_WORK
        assert 6.1 <= result.score <= 8.0

    def test_peak_mode(self):
        """DCS 8.1–10.0 → PEAK"""
        result = calculate_dcs(10, 10, 9, 1)
        assert result.mode == Mode.PEAK
        assert result.score >= 8.1


class TestDCSValidation:
    """Test input validation."""

    def test_energy_below_range(self):
        with pytest.raises(ValueError):
            calculate_dcs(0, 5, 5, 5)

    def test_energy_above_range(self):
        with pytest.raises(ValueError):
            calculate_dcs(11, 5, 5, 5)

    def test_mood_below_range(self):
        with pytest.raises(ValueError):
            calculate_dcs(5, 0, 5, 5)

    def test_sleep_above_range(self):
        with pytest.raises(ValueError):
            calculate_dcs(5, 5, 11, 5)

    def test_stress_below_range(self):
        with pytest.raises(ValueError):
            calculate_dcs(5, 5, 5, 0)

    def test_stress_above_range(self):
        with pytest.raises(ValueError):
            calculate_dcs(5, 5, 5, 11)


class TestDCSResult:
    """Test DCSResult dataclass."""

    def test_result_has_all_fields(self):
        result = calculate_dcs(5, 5, 5, 5)
        assert isinstance(result, DCSResult)
        assert isinstance(result.score, float)
        assert isinstance(result.mode, Mode)
        assert isinstance(result.mode_description, str)
        assert isinstance(result.recommended_task_types, list)
        assert len(result.recommended_task_types) > 0

    def test_survival_task_recommendations(self):
        result = calculate_dcs(1, 1, 1, 10)
        assert any("non-negotiable" in t.lower() for t in result.recommended_task_types)

    def test_peak_task_recommendations(self):
        result = calculate_dcs(10, 10, 10, 1)
        assert any("ambitious" in t.lower() for t in result.recommended_task_types)
