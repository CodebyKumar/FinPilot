'use client';

import { ReactNode, CSSProperties } from 'react';

interface BadgeProps {
  children: ReactNode;
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info';
  style?: CSSProperties;
}

export function Badge({ children, variant = 'default', style }: BadgeProps) {
  const variantStyles: Record<string, CSSProperties> = {
    default: {
      background: 'var(--bg3)',
      color: 'var(--text)',
      border: '1px solid var(--border)',
    },
    success: {
      background: 'rgba(16, 185, 129, 0.1)',
      color: 'var(--emerald)',
      border: '1px solid var(--emerald)',
    },
    warning: {
      background: 'rgba(245, 158, 11, 0.1)',
      color: 'var(--amber)',
      border: '1px solid var(--amber)',
    },
    error: {
      background: 'rgba(244, 63, 94, 0.1)',
      color: 'var(--rose)',
      border: '1px solid var(--rose)',
    },
    info: {
      background: 'rgba(56, 189, 248, 0.1)',
      color: 'var(--sky)',
      border: '1px solid var(--sky)',
    },
  };

  return (
    <span
      style={{
        display: 'inline-block',
        padding: '0.25rem 0.75rem',
        borderRadius: '0.375rem',
        fontSize: '0.85rem',
        fontWeight: 600,
        ...variantStyles[variant],
        ...style,
      }}
    >
      {children}
    </span>
  );
}
