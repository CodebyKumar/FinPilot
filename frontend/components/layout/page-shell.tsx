'use client';

import { ReactNode, CSSProperties } from 'react';

interface PageShellProps {
  title: string;
  subtitle?: string;
  children: ReactNode;
  headerAction?: ReactNode;
  headerStyle?: CSSProperties;
}

export function PageShell({
  title,
  subtitle,
  children,
  headerAction,
  headerStyle,
}: PageShellProps) {
  return (
    <div>
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: '1rem',
          marginBottom: '2rem',
          ...headerStyle,
        }}
      >
        <div>
          <h1 style={{
            fontSize: '2rem',
            fontFamily: 'Syne',
            fontWeight: 700,
            margin: '0 0 0.5rem 0',
          }}>
            {title}
          </h1>
          {subtitle && (
            <p style={{
              fontSize: '1rem',
              color: 'var(--muted)',
              margin: 0,
            }}>
              {subtitle}
            </p>
          )}
        </div>
        {headerAction && <div>{headerAction}</div>}
      </div>
      {children}
    </div>
  );
}
