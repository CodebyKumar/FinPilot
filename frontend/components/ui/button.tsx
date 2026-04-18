'use client';

import { ReactNode, CSSProperties } from 'react';

interface ButtonProps {
  children: ReactNode;
  onClick?: () => void;
  variant?: 'primary' | 'secondary' | 'danger' | 'success';
  disabled?: boolean;
  type?: 'button' | 'submit' | 'reset';
  style?: CSSProperties;
}

export function Button({
  children,
  onClick,
  variant = 'primary',
  disabled = false,
  type = 'button',
  style,
}: ButtonProps) {
  const baseStyles: CSSProperties = {
    padding: '0.75rem 1.5rem',
    border: 'none',
    borderRadius: '0.5rem',
    cursor: disabled ? 'not-allowed' : 'pointer',
    fontWeight: 600,
    fontSize: '1rem',
    transition: 'all 0.2s ease',
    opacity: disabled ? 0.5 : 1,
  };

  const variantStyles: Record<string, CSSProperties> = {
    primary: {
      background: 'var(--indigo)',
      color: 'white',
    },
    secondary: {
      background: 'var(--bg3)',
      color: 'var(--text)',
      border: '1px solid var(--border)',
    },
    danger: {
      background: 'var(--rose)',
      color: 'white',
    },
    success: {
      background: 'var(--emerald)',
      color: 'white',
    },
  };

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      style={{ ...baseStyles, ...variantStyles[variant], ...style }}
    >
      {children}
    </button>
  );
}
