import React, { useMemo } from 'react';
import './TreeOrganism.css';

// A geometric, architectural tree SVG — circuit/bonsai hybrid
export default function TreeOrganism({ compositeScore = 5.0, size = 220, compact = false }) {
  const state = useMemo(() => {
    if (compositeScore < 2.0) return 'dead';
    if (compositeScore < 4.0) return 'struggling';
    if (compositeScore < 6.0) return 'growing';
    if (compositeScore < 8.0) return 'thriving';
    return 'peak';
  }, [compositeScore]);

  const stateLabel = {
    dead: 'Systems critical.',
    struggling: 'Needs attention.',
    growing: 'Moving forward.',
    thriving: 'Thriving. Keep going.',
    peak: 'Peak condition.',
  };

  // Dynamic opacities based on state
  const rootOpacity = state === 'dead' ? 0.2 : state === 'struggling' ? 0.4 : state === 'growing' ? 0.6 : 1;
  const canopyOpacity = state === 'dead' ? 0.1 : state === 'struggling' ? 0.3 : state === 'growing' ? 0.5 : state === 'thriving' ? 0.8 : 1;
  const glowIntensity = state === 'peak' ? 0.6 : state === 'thriving' ? 0.35 : state === 'growing' ? 0.15 : 0.05;
  const leafCount = state === 'dead' ? 0 : state === 'struggling' ? 3 : state === 'growing' ? 6 : state === 'thriving' ? 10 : 14;
  const sparkActive = state === 'peak';

  return (
    <div className={`tree-organism tree-state-${state} ${compact ? 'tree-compact' : ''}`}>
      <svg
        viewBox="0 0 200 260"
        width={compact ? 120 : size}
        height={compact ? 150 : (size * 1.18)}
        className="tree-svg"
      >
        <defs>
          <radialGradient id="trunkGlow" cx="50%" cy="60%">
            <stop offset="0%" stopColor="var(--gold)" stopOpacity={glowIntensity} />
            <stop offset="100%" stopColor="transparent" stopOpacity="0" />
          </radialGradient>
          <filter id="softGlow">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Ambient glow */}
        <circle cx="100" cy="130" r="80" fill="url(#trunkGlow)" />

        {/* Roots — 4 factions */}
        <g className="tree-roots" opacity={rootOpacity}>
          {/* Health root */}
          <path d="M90 200 L70 235 L55 250" stroke="var(--health)" strokeWidth="2" fill="none"
                className="tree-root root-health" />
          <circle cx="55" cy="250" r="3" fill="var(--health)" className="root-node" opacity={rootOpacity} />

          {/* Leverage root */}
          <path d="M105 200 L125 240 L140 255" stroke="var(--leverage)" strokeWidth="2" fill="none"
                className="tree-root root-leverage" />
          <circle cx="140" cy="255" r="3" fill="var(--leverage)" className="root-node" opacity={rootOpacity} />

          {/* Craft root */}
          <path d="M95 200 L80 245 L70 258" stroke="var(--craft)" strokeWidth="2" fill="none"
                className="tree-root root-craft" />
          <circle cx="70" cy="258" r="2.5" fill="var(--craft)" className="root-node" opacity={rootOpacity} />

          {/* Expression root */}
          <path d="M110 200 L130 248 L150 258" stroke="var(--expression)" strokeWidth="2" fill="none"
                className="tree-root root-expression" />
          <circle cx="150" cy="258" r="2.5" fill="var(--expression)" className="root-node" opacity={rootOpacity} />
        </g>

        {/* Trunk */}
        <path d="M100 200 L100 120" stroke="var(--text-tertiary)" strokeWidth="3" fill="none"
              className="tree-trunk" opacity={state === 'dead' ? 0.3 : 0.7} />
        <path d="M100 180 L100 130" stroke="var(--gold)" strokeWidth="2" fill="none"
              className="tree-trunk-inner" opacity={glowIntensity * 2} filter="url(#softGlow)" />

        {/* Branches */}
        <g className="tree-branches" opacity={canopyOpacity}>
          {/* Main branches */}
          <path d="M100 160 L60 130" stroke="var(--text-tertiary)" strokeWidth="1.5" fill="none" />
          <path d="M100 160 L140 125" stroke="var(--text-tertiary)" strokeWidth="1.5" fill="none" />
          <path d="M100 140 L55 100" stroke="var(--text-tertiary)" strokeWidth="1.5" fill="none" />
          <path d="M100 140 L145 95" stroke="var(--text-tertiary)" strokeWidth="1.5" fill="none" />
          <path d="M100 130 L75 80" stroke="var(--text-tertiary)" strokeWidth="1" fill="none" />
          <path d="M100 130 L125 75" stroke="var(--text-tertiary)" strokeWidth="1" fill="none" />
          <path d="M100 120 L100 60" stroke="var(--text-tertiary)" strokeWidth="1" fill="none" />

          {/* Sub-branches */}
          <path d="M60 130 L40 110" stroke="var(--text-tertiary)" strokeWidth="1" fill="none" opacity="0.7" />
          <path d="M140 125 L160 105" stroke="var(--text-tertiary)" strokeWidth="1" fill="none" opacity="0.7" />
          <path d="M55 100 L35 75" stroke="var(--text-tertiary)" strokeWidth="1" fill="none" opacity="0.6" />
          <path d="M145 95 L165 70" stroke="var(--text-tertiary)" strokeWidth="1" fill="none" opacity="0.6" />
        </g>

        {/* Leaf nodes */}
        <g className="tree-leaves">
          {leafCount >= 1 && <circle cx="60" cy="130" r="4" fill="var(--health)" opacity={canopyOpacity} className="leaf" />}
          {leafCount >= 2 && <circle cx="140" cy="125" r="4" fill="var(--leverage)" opacity={canopyOpacity} className="leaf" />}
          {leafCount >= 3 && <circle cx="55" cy="100" r="4.5" fill="var(--craft)" opacity={canopyOpacity} className="leaf" />}
          {leafCount >= 4 && <circle cx="145" cy="95" r="4.5" fill="var(--expression)" opacity={canopyOpacity} className="leaf" />}
          {leafCount >= 5 && <circle cx="100" cy="60" r="5" fill="var(--gold)" opacity={canopyOpacity} className="leaf" />}
          {leafCount >= 6 && <circle cx="75" cy="80" r="3.5" fill="var(--health)" opacity={canopyOpacity * 0.8} className="leaf" />}
          {leafCount >= 7 && <circle cx="125" cy="75" r="3.5" fill="var(--leverage)" opacity={canopyOpacity * 0.8} className="leaf" />}
          {leafCount >= 8 && <circle cx="40" cy="110" r="3" fill="var(--craft)" opacity={canopyOpacity * 0.7} className="leaf" />}
          {leafCount >= 9 && <circle cx="160" cy="105" r="3" fill="var(--expression)" opacity={canopyOpacity * 0.7} className="leaf" />}
          {leafCount >= 10 && <circle cx="35" cy="75" r="3" fill="var(--health)" opacity={canopyOpacity * 0.6} className="leaf" />}
          {leafCount >= 11 && <circle cx="165" cy="70" r="3" fill="var(--leverage)" opacity={canopyOpacity * 0.6} className="leaf" />}
          {leafCount >= 12 && <circle cx="90" cy="50" r="3" fill="var(--craft)" opacity={canopyOpacity * 0.8} className="leaf" />}
          {leafCount >= 13 && <circle cx="110" cy="45" r="3" fill="var(--expression)" opacity={canopyOpacity * 0.8} className="leaf" />}
          {leafCount >= 14 && <circle cx="100" cy="40" r="4" fill="var(--gold)" opacity={canopyOpacity} className="leaf top-leaf" />}
        </g>

        {/* Peak spark */}
        {sparkActive && (
          <circle cx="100" cy="200" r="3" fill="var(--gold)" className="tree-spark" filter="url(#softGlow)" />
        )}
      </svg>

      {!compact && (
        <p className="tree-label display-m" style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>
          {stateLabel[state]}
        </p>
      )}
    </div>
  );
}
