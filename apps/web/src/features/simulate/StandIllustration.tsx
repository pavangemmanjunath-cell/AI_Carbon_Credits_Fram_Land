import { useMemo } from 'react';
import { ndviColor } from '@/lib/ndvi';
import { standLayout } from './logic/standIllustration';

interface Props {
  treeCount: number;
  /** 0–1 canopy size from the stand's age (see growthFactor). */
  growth: number;
  /** Illustrative canopy tone only — never shown as a number. */
  canopyTone: number;
  label: string;
}

/** Light SVG stand: rows of simple tree glyphs that grow with the selected year. No WebGL. */
export function StandIllustration({ treeCount, growth, canopyTone, label }: Props) {
  const layout = useMemo(() => standLayout(treeCount, growth), [treeCount, growth]);
  const canopy = ndviColor(canopyTone);
  const maxCanopy = 30;
  const maxTrunk = 34;
  return (
    // Sky and ground extend past the viewBox (overflow visible) so a taller or wider frame has no empty bands.
    <svg
      viewBox={`0 0 ${layout.width} ${layout.height}`}
      role="img"
      aria-label={label}
      className="block h-full w-full overflow-visible"
      preserveAspectRatio="xMidYMid meet"
    >
      <defs>
        <linearGradient id="stand-sky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#E8F1F7" />
          <stop offset="100%" stopColor="#F4F8EF" />
        </linearGradient>
        <linearGradient id="stand-ground" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#D9E6C9" />
          <stop offset="100%" stopColor="#C4D7AE" />
        </linearGradient>
      </defs>
      <rect
        x={-2000}
        y={-2000}
        width={layout.width + 4000}
        height={layout.horizon + 2000}
        fill="#E8F1F7"
      />
      <rect
        x={-2000}
        y={0}
        width={layout.width + 4000}
        height={layout.horizon}
        fill="url(#stand-sky)"
      />
      <rect
        x={-2000}
        y={layout.horizon}
        width={layout.width + 4000}
        height={layout.height - layout.horizon + 2000}
        fill="#C4D7AE"
      />
      <rect
        x={-2000}
        y={layout.horizon}
        width={layout.width + 4000}
        height={layout.height - layout.horizon}
        fill="url(#stand-ground)"
      />
      <path
        d={`M0 ${layout.horizon + 4} Q ${layout.width / 2} ${layout.horizon - 10} ${layout.width} ${layout.horizon + 4}`}
        fill="none"
        stroke="#B5C9A0"
        strokeWidth="2"
      />
      {layout.glyphs.map((glyph) => {
        const s = Math.max(0.12, glyph.scale);
        const trunkH = 6 + maxTrunk * s;
        const r = 5 + maxCanopy * s;
        return (
          <g key={`${glyph.row}-${glyph.x}`}>
            <ellipse
              cx={glyph.x}
              cy={glyph.y + 1}
              rx={r * 0.8}
              ry={Math.max(2, r * 0.18)}
              fill="#9DB88A"
              opacity="0.55"
            />
            <rect
              x={glyph.x - 1.5 - s * 2}
              y={glyph.y - trunkH}
              width={3 + s * 4}
              height={trunkH}
              rx="1.5"
              fill="#7A5A3A"
            />
            <circle cx={glyph.x} cy={glyph.y - trunkH - r * 0.6} r={r} fill={canopy} />
            <circle
              cx={glyph.x - r * 0.35}
              cy={glyph.y - trunkH - r * 0.85}
              r={r * 0.45}
              fill="#FFFFFF"
              opacity="0.14"
            />
          </g>
        );
      })}
    </svg>
  );
}
