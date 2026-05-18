/**
 * Typed token references for use in TS (chart series colours, inline style props).
 * Do NOT add new hex literals — add a new CSS token in tokens.css and re-export here.
 */
export const tokens = {
  surface: {
    page: "var(--surface-page)",
    card: "var(--surface-card)",
    row: "var(--surface-row)",
    rowHover: "var(--surface-row-hover)",
    sidebar: "var(--surface-sidebar)",
    overlay: "var(--surface-overlay)",
  },
  border: {
    subtle: "var(--border-subtle)",
    default: "var(--border-default)",
    strong: "var(--border-strong)",
    focus: "var(--border-focus)",
  },
  text: {
    primary: "var(--text-primary)",
    secondary: "var(--text-secondary)",
    muted: "var(--text-muted)",
    disabled: "var(--text-disabled)",
    inverse: "var(--text-inverse)",
  },
  accent: {
    default: "var(--accent-default)",
    hover: "var(--accent-hover)",
    active: "var(--accent-active)",
    bgSoft: "var(--accent-bg-soft)",
    fg: "var(--accent-fg)",
  },
  semantic: {
    success: { fg: "var(--success-fg)", bgSoft: "var(--success-bg-soft)", border: "var(--success-border)" },
    warning: { fg: "var(--warning-fg)", bgSoft: "var(--warning-bg-soft)", border: "var(--warning-border)" },
    danger:  { fg: "var(--danger-fg)",  bgSoft: "var(--danger-bg-soft)",  border: "var(--danger-border)"  },
    info:    { fg: "var(--info-fg)",    bgSoft: "var(--info-bg-soft)",    border: "var(--info-border)"    },
  },
  dataViz: [
    "var(--data-series-1)",
    "var(--data-series-2)",
    "var(--data-series-3)",
    "var(--data-series-4)",
    "var(--data-series-5)",
    "var(--data-series-6)",
  ],
} as const;
