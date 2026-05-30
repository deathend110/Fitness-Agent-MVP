function ShellIcon({ className = 'h-5 w-5', name }) {
  const commonProps = {
    className,
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: '1.8',
    viewBox: '0 0 24 24',
  }

  switch (name) {
    case 'profile':
      return (
        <svg aria-hidden="true" {...commonProps}>
          <path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z" />
          <path d="M5 20a7 7 0 0 1 14 0" />
        </svg>
      )
    case 'plan':
      return (
        <svg aria-hidden="true" {...commonProps}>
          <path d="M7 3v4" />
          <path d="M17 3v4" />
          <rect height="15" rx="2.5" width="18" x="3" y="5" />
          <path d="M3 10h18" />
        </svg>
      )
    case 'today':
      return (
        <svg aria-hidden="true" {...commonProps}>
          <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" />
          <path d="M9 3h6v4H9z" />
          <path d="M9 12h6" />
          <path d="M9 16h4" />
        </svg>
      )
    case 'coach':
      return (
        <svg aria-hidden="true" {...commonProps}>
          <path d="M12 3v2" />
          <path d="M18.36 5.64 16.95 7.05" />
          <path d="M21 12h-2" />
          <path d="m7.05 7.05-1.41-1.41" />
          <path d="M6 12H4" />
          <path d="M9 18h6" />
          <path d="M10 21h4" />
          <path d="M8.5 14.5a5 5 0 1 1 7 0c-.83.74-1.33 1.8-1.33 2.92V18h-4.34v-.58c0-1.12-.5-2.18-1.33-2.92Z" />
        </svg>
      )
    case 'settings':
      return (
        <svg aria-hidden="true" {...commonProps}>
          <path d="M10.33 4.32c.4-1.76 2.94-1.76 3.34 0a1.73 1.73 0 0 0 2.58 1.07c1.54-.94 3.31.83 2.37 2.37a1.73 1.73 0 0 0 1.07 2.58c1.76.4 1.76 2.94 0 3.34a1.73 1.73 0 0 0-1.07 2.58c.94 1.54-.83 3.31-2.37 2.37a1.73 1.73 0 0 0-2.58 1.07c-.4 1.76-2.94 1.76-3.34 0a1.73 1.73 0 0 0-2.58-1.07c-1.54.94-3.31-.83-2.37-2.37a1.73 1.73 0 0 0-1.07-2.58c-1.76-.4-1.76-2.94 0-3.34a1.73 1.73 0 0 0 1.07-2.58c-.94-1.54.83-3.31 2.37-2.37a1.73 1.73 0 0 0 2.58-1.07Z" />
          <circle cx="12" cy="12" r="3" />
        </svg>
      )
    case 'spark':
      return (
        <svg aria-hidden="true" {...commonProps}>
          <path d="m12 3 1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8Z" />
          <path d="M19 3v4" />
          <path d="M21 5h-4" />
        </svg>
      )
    case 'storage':
      return (
        <svg aria-hidden="true" {...commonProps}>
          <ellipse cx="12" cy="6" rx="7" ry="3" />
          <path d="M5 6v6c0 1.66 3.13 3 7 3s7-1.34 7-3V6" />
          <path d="M5 12v6c0 1.66 3.13 3 7 3s7-1.34 7-3v-6" />
        </svg>
      )
    case 'check':
      return (
        <svg aria-hidden="true" {...commonProps}>
          <circle cx="12" cy="12" r="8" />
          <path d="m8.5 12.5 2.2 2.2 4.8-5.2" />
        </svg>
      )
    default:
      return null
  }
}

export default ShellIcon
