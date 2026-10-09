interface LogoProps {
  size?: number;
  className?: string;
}

/** Original mark: rounded forest-green square with a white leaf and a highlight dot. */
export function LogoMark({ size = 32, className }: LogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 36 36"
      fill="none"
      aria-hidden="true"
      className={className}
    >
      <rect width="36" height="36" rx="9" fill="var(--forest)" />
      <path d="M10 26c0-9 6.5-15 16.5-15C25.5 21 20 26 11.5 26" fill="#FFFFFF" />
      <path
        d="M12.5 24.5c3-4.2 6.2-7.3 11-10.3"
        stroke="var(--forest)"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
      <circle cx="27.5" cy="8.5" r="2.2" fill="var(--mint-on-dark)" />
    </svg>
  );
}

export function Wordmark({ compact = false }: { compact?: boolean }) {
  return (
    <span className="flex flex-col leading-tight">
      <span className="font-heading text-[16px] font-bold tracking-tight text-ink">
        AgriCarbon Atlas
      </span>
      {!compact && (
        <span className="text-[11px] text-muted">Trees, land and carbon potential</span>
      )}
    </span>
  );
}
