'use client';

import { ReactNode, CSSProperties } from 'react';

interface CardProps {
  children: ReactNode;
  title?: string;
  subtitle?: string;
  style?: CSSProperties;
  headerStyle?: CSSProperties;
}

export function Card({ children, title, subtitle, style, headerStyle }: CardProps) {
  return (
    <div
      style={{
        background: 'var(--bg2)',
        border: '1px solid var(--border)',
        borderRadius: '0.75rem',
        padding: '1.5rem',
        ...style,
      }}
    >
      {(title || subtitle) && (
        <div style={{ marginBottom: '1rem', ...headerStyle }}>
          {title && (
            <h3 style={{
              fontSize: '1.25rem',
              fontFamily: 'Syne',
              fontWeight: 700,
              margin: '0 0 0.25rem 0',
            }}>
              {title}
            </h3>
          )}
          {subtitle && (
            <p style={{
              fontSize: '0.9rem',
              color: 'var(--muted)',
              margin: 0,
            }}>
              {subtitle}
            </p>
          )}
        </div>
      )}
      {children}
    </div>
  );
}
