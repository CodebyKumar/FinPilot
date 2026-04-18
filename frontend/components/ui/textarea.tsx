'use client';

import { TextareaHTMLAttributes, CSSProperties } from 'react';

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  containerStyle?: CSSProperties;
}

export function Textarea({
  label,
  error,
  containerStyle,
  ...props
}: TextareaProps) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', ...containerStyle }}>
      {label && (
        <label style={{
          fontSize: '0.9rem',
          fontWeight: 600,
          color: 'var(--text)',
        }}>
          {label}
        </label>
      )}
      <textarea
        {...props}
        style={{
          padding: '0.75rem',
          background: 'var(--bg3)',
          border: error ? '1px solid var(--rose)' : '1px solid var(--border)',
          borderRadius: '0.5rem',
          color: 'var(--text)',
          fontSize: '1rem',
          fontFamily: 'DM Sans, sans-serif',
          minHeight: '120px',
          resize: 'vertical',
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
