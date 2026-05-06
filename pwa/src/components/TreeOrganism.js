import React, { useMemo } from 'react';
import './TreeOrganism.css';

export default function TreeOrganism({ compositeScore = 5.0, size = 220, compact = false }) {
  const state = useMemo(() => {
    if (compositeScore < 2.0) return 'dead';
    if (compositeScore < 4.0) return 'struggling';
    if (compositeScore < 6.0) return 'growing';
    if (compositeScore < 8.0) return 'thriving';
    return 'peak';
  }, [compositeScore]);

  const stateLabel = {
    dead: 'SYSTEMS CRITICAL',
    struggling: 'NEEDS ATTENTION',
    growing: 'MOVING FORWARD',
    thriving: 'THRIVING',
    peak: 'PEAK CONDITION',
  };

  const { branches, leaves } = useMemo(() => {
    let maxDepth = 6;
    let leavesProb = 1.0;
    
    if (state === 'dead') {
       maxDepth = 3;
       leavesProb = 0.0; // Handled specially below
    } else if (state === 'struggling') {
       maxDepth = 4;
       leavesProb = 0.3;
    } else if (state === 'growing') {
       maxDepth = 5;
       leavesProb = 0.6;
    } else if (state === 'thriving') {
       maxDepth = 6;
       leavesProb = 0.85;
    } else if (state === 'peak') {
       maxDepth = 7;
       leavesProb = 1.0;
    }

    const b = [];
    const l = [];
    
    const build = (x, y, len, angle, depth, path) => {
      const endX = x + len * Math.sin(angle);
      const endY = y - len * Math.cos(angle);
      
      const width = state === 'peak' ? Math.max(2, (8 - depth)*1.2) : Math.max(1, (7 - depth));
      
      b.push({ id: `b-${path}`, x1: x, y1: y, x2: endX, y2: endY, width });
      
      const seed = path.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
      const hash = (n) => {
         let val = Math.sin(seed * 13.37 + n * 42.42) * 10000;
         return val - Math.floor(val);
      };

      if (depth < maxDepth) {
        const spread1 = 0.3 + hash(1) * 0.4;
        const spread2 = 0.3 + hash(2) * 0.4;
        
        const len1 = len * (0.7 + hash(3)*0.15);
        const len2 = len * (0.7 + hash(4)*0.15);
        
        build(endX, endY, len1, angle - spread1, depth + 1, path + 'L');
        build(endX, endY, len2, angle + spread2, depth + 1, path + 'R');
        
        if (hash(5) > 0.6 && depth > 1) {
           build(endX, endY, len * 0.5, angle + (hash(6) - 0.5)*0.3, depth + 1, path + 'M');
        }
      } else {
        if (state !== 'dead' && hash(7) < leavesProb) {
           // Unified color instead of multicolored dots
           const color = 'var(--text-primary)';
           l.push({ id: `l-${path}`, x: endX, y: endY, color, size: 4 + hash(9)*3 });
        }
      }
    };
    
    build(100, 190, 45, 0, 1, 'T');
    
    if (state === 'dead') {
       // Just one leaf holding on for dear life
       const tip = b[b.length - 1];
       l.push({ id: 'l-last-leaf', x: tip.x2, y: tip.y2, color: 'var(--health)', size: 5, isLastLeaf: true });
    }
    
    return { branches: b, leaves: l };
  }, [state]);

  return (
    <div className={`node-organism org-state-${state} ${compact ? 'org-compact' : ''}`}>
      <svg
        viewBox="0 0 200 200"
        width={compact ? 120 : size}
        height={compact ? 120 : size}
        className="org-svg"
      >
        {branches.map(branch => (
          <line
            key={branch.id}
            x1={branch.x1} y1={branch.y1} x2={branch.x2} y2={branch.y2}
            stroke="var(--text-primary)"
            strokeWidth={branch.width}
            strokeLinecap="square"
            className="tree-branch"
          />
        ))}
        {leaves.map(leaf => (
          <rect
            key={leaf.id}
            x={leaf.x - leaf.size/2} 
            y={leaf.y - leaf.size/2} 
            width={leaf.size} 
            height={leaf.size}
            fill={leaf.color}
            stroke="var(--text-primary)"
            strokeWidth="2"
            className={`tree-leaf ${leaf.isLastLeaf ? 'blowing-leaf' : ''}`}
            style={{ transformOrigin: `${leaf.x}px ${leaf.y}px` }}
          />
        ))}
      </svg>
      {!compact && (
        <p className="org-label heading-1">
          {stateLabel[state]}
        </p>
      )}
    </div>
  );
}
