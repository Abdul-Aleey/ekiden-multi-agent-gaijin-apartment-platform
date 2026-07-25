export default function Logo({ size = 36 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="ekidenGrad" x1="0" y1="0" x2="48" y2="48" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#4F46E5" />
          <stop offset="55%" stopColor="#7C3AED" />
          <stop offset="100%" stopColor="#C4342B" />
        </linearGradient>
      </defs>
      {/* three relay batons handing off — the Ekiden (relay) motif */}
      <circle cx="24" cy="24" r="22" fill="url(#ekidenGrad)" opacity="0.12" />
      <path
        d="M8 32 L18 20"
        stroke="url(#ekidenGrad)"
        strokeWidth="4"
        strokeLinecap="round"
      />
      <path
        d="M18 20 L28 30"
        stroke="url(#ekidenGrad)"
        strokeWidth="4"
        strokeLinecap="round"
      />
      <path
        d="M28 30 L40 16"
        stroke="url(#ekidenGrad)"
        strokeWidth="4"
        strokeLinecap="round"
      />
      <circle cx="8" cy="32" r="3.5" fill="url(#ekidenGrad)" />
      <circle cx="18" cy="20" r="3.5" fill="url(#ekidenGrad)" />
      <circle cx="28" cy="30" r="3.5" fill="url(#ekidenGrad)" />
      <circle cx="40" cy="16" r="3.5" fill="url(#ekidenGrad)" />
    </svg>
  );
}
