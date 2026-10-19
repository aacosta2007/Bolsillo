/** Anillo de progreso (SVG, como en el diseño de Metas). */
export function GoalRing({ percent, color, label }: { percent: number; color: string; label: string }) {
  const C = 2 * Math.PI * 15;
  const p = Math.max(0, Math.min(100, percent)) / 100;
  return (
    <svg width="64" height="64" viewBox="0 0 36 36" role="img" aria-label={label} className="shrink-0">
      <circle cx="18" cy="18" r="15" fill="none" stroke="#EEF1EE" strokeWidth="4" />
      <circle
        cx="18"
        cy="18"
        r="15"
        fill="none"
        stroke={color}
        strokeWidth="4"
        strokeLinecap="round"
        strokeDasharray={`${(C * p).toFixed(1)} ${C.toFixed(1)}`}
        transform="rotate(-90 18 18)"
      />
      <text x="18" y="21" textAnchor="middle" fontSize="8.5" fontWeight="700" fill="#16201B" fontFamily="Figtree, sans-serif">
        {Math.round(percent)}%
      </text>
    </svg>
  );
}
