// Helper utilities for Locus PWA

export function getGreeting() {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  if (hour < 21) return 'Good evening';
  return 'Good night';
}

export function formatDate(date = new Date()) {
  return date.toLocaleDateString('en-GB', {
    weekday: 'long',
    day: 'numeric',
    month: 'short',
  });
}

export function formatTime(date = new Date()) {
  return date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
}

export function getModeColor(mode) {
  const colors = {
    SURVIVAL: 'var(--mode-survival)',
    RECOVERY: 'var(--mode-recovery)',
    NORMAL: 'var(--mode-normal)',
    DEEP_WORK: 'var(--mode-deep-work)',
    PEAK: 'var(--mode-peak)',
  };
  return colors[mode] || 'var(--text-secondary)';
}

export function getModeBgColor(mode) {
  const colors = {
    SURVIVAL: 'rgba(196, 107, 107, 0.12)',
    RECOVERY: 'rgba(212, 168, 83, 0.12)',
    NORMAL: 'rgba(91, 143, 191, 0.12)',
    DEEP_WORK: 'rgba(90, 158, 120, 0.12)',
    PEAK: 'rgba(201, 169, 110, 0.15)',
  };
  return colors[mode] || 'var(--bg-2)';
}

export function getModeLabel(mode) {
  const labels = {
    SURVIVAL: 'SURVIVAL',
    RECOVERY: 'RECOVERY',
    NORMAL: 'NORMAL',
    DEEP_WORK: 'DEEP WORK',
    PEAK: 'PEAK',
  };
  return labels[mode] || mode;
}

export function getModeDescription(mode) {
  const desc = {
    SURVIVAL: 'Protect what\'s essential. Nothing else.',
    RECOVERY: 'Gentle progress. No forcing.',
    NORMAL: 'A full, balanced day is yours.',
    DEEP_WORK: 'Prioritise your hardest work.',
    PEAK: 'This is rare. Make it count.',
  };
  return desc[mode] || '';
}

export function getFactionColor(faction) {
  const colors = {
    health: 'var(--health)',
    leverage: 'var(--leverage)',
    craft: 'var(--craft)',
    expression: 'var(--expression)',
  };
  return colors[faction] || 'var(--text-secondary)';
}

export function getFactionDimColor(faction) {
  const colors = {
    health: 'var(--health-dim)',
    leverage: 'var(--leverage-dim)',
    craft: 'var(--craft-dim)',
    expression: 'var(--expression-dim)',
  };
  return colors[faction] || 'var(--bg-2)';
}

export function getFactionLabel(faction) {
  const labels = {
    health: 'Health',
    leverage: 'Leverage',
    craft: 'Craft',
    expression: 'Expression',
  };
  return labels[faction] || faction;
}

export function calculateDCS(e, m, s, st) {
  const dcs = Math.round(((e + m + s) / 3) * (1 - st / 20) * 100) / 100;
  const clamped = Math.max(0, Math.min(10, dcs));
  let mode;
  if (clamped <= 2.0) mode = 'SURVIVAL';
  else if (clamped <= 4.0) mode = 'RECOVERY';
  else if (clamped <= 6.0) mode = 'NORMAL';
  else if (clamped <= 8.0) mode = 'DEEP_WORK';
  else mode = 'PEAK';
  return { dcs: clamped, mode };
}

export function calculateTWS(priority, urgency, difficulty) {
  return Math.round(((priority * 0.4) + (urgency * 0.4) + (difficulty * 0.2)) * 100) / 100;
}

// Animated counter (requestAnimationFrame)
export function animateValue(ref, start, end, duration = 800) {
  if (!ref.current) return;
  const startTime = performance.now();
  const range = end - start;

  function update(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    // Ease out cubic
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = start + range * eased;
    if (ref.current) {
      ref.current.textContent = current.toFixed(1);
    }
    if (progress < 1) requestAnimationFrame(update);
  }
  requestAnimationFrame(update);
}

export function getTreeState(compositeScore) {
  if (compositeScore < 2.0) return { state: 'dead', label: 'Systems critical.', color: 'var(--bg-4)' };
  if (compositeScore < 4.0) return { state: 'struggling', label: 'Needs attention.', color: 'var(--warning)' };
  if (compositeScore < 6.0) return { state: 'growing', label: 'Moving forward.', color: 'var(--text-secondary)' };
  if (compositeScore < 8.0) return { state: 'thriving', label: 'Thriving.', color: 'var(--gold)' };
  return { state: 'peak', label: 'Peak condition.', color: 'var(--gold)' };
}
