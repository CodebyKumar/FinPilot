'use client';

import { InputHTMLAttributes, CSSProperties } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  containerStyle?: CSSProperties;
}

export function Input({
  label,
  error,
  containerStyle,
  ...props
}: InputProps) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '0.5rem',
        width: '100%',
        minWidth: 0,
        ...containerStyle,
      }}
    >
      {label && (
        <label style={{
          fontSize: '0.9rem',
          fontWeight: 600,
          color: 'var(--text)',
        }}>
          {label}
        </label>
      )}
      <input
        {...props}
        style={{
          padding: '0.75rem',
          background: 'var(--bg3)',
          border: error ? '1px solid var(--rose)' : '1px solid var(--border)',
          borderRadius: '0.5rem',
          color: 'var(--text)',
          fontSize: '1rem',
          width: '100%',
          minWidth: 0,
          boxSizing: 'border-box',
          ...props.style,
        }}
      />
      {error && (
        <p style={{ fontSize: '0.85rem', color: 'var(--rose)', margin: 0 }}>
          {error}
        </p>
      )}
    </div>
  );
}
