import { calculateDCS, getModeFromDCS } from './helpers';

describe('calculateDCS', () => {
  test('calculates correct DCS for typical values', () => {
    // (5 * 0.3) + (5 * 0.3) + (5 * 0.2) + (5 * 0.2) = 1.5 + 1.5 + 1.0 + 1.0 = 5.0
    expect(calculateDCS(5, 5, 5, 5)).toBe(5.0);
  });

  test('calculates correct DCS for maximum values', () => {
    // (10 * 0.3) + (10 * 0.3) + (10 * 0.2) + (10 * 0.2) = 3 + 3 + 2 + 2 = 10.0
    expect(calculateDCS(10, 10, 10, 10)).toBe(10.0);
  });

  test('calculates correct DCS for minimum values', () => {
    expect(calculateDCS(0, 0, 0, 0)).toBe(0.0);
  });

  test('calculates correct DCS for mixed values', () => {
    // (10 * 0.3) + (5 * 0.3) + (8 * 0.2) + (2 * 0.2) = 3.0 + 1.5 + 1.6 + 0.4 = 6.5
    expect(calculateDCS(10, 5, 8, 2)).toBe(6.5);
  });
});

describe('getModeFromDCS', () => {
  test('returns SURVIVAL when dcs is 2.0', () => {
    expect(getModeFromDCS(2.0)).toBe('SURVIVAL');
  });

  test('returns RECOVERY when dcs is 4.0', () => {
    expect(getModeFromDCS(4.0)).toBe('RECOVERY');
  });

  test('returns NORMAL when dcs is 6.0', () => {
    expect(getModeFromDCS(6.0)).toBe('NORMAL');
  });

  test('returns DEEP_WORK when dcs is 8.0', () => {
    expect(getModeFromDCS(8.0)).toBe('DEEP_WORK');
  });

  test('returns PEAK when dcs is 8.1', () => {
    expect(getModeFromDCS(8.1)).toBe('PEAK');
  });

  test('clamped to 0 for negative values', () => {
    expect(getModeFromDCS(-1)).toBe('SURVIVAL');
  });

  test('clamped to 10 for large values', () => {
    expect(getModeFromDCS(20)).toBe('PEAK');
  });
});
