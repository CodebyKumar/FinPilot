'use client';

import { ReactNode } from 'react';

interface SkeletonProps {
  width?: string;
  height?: string;
  count?: number;
  style?: Record<string, string>;
}

export function Skeleton({ width = '100%', height = '20px', count = 1, style }: SkeletonProps) {
  return (
    <>
      {Array.from({ length: count }).map((_, idx) => (
        <div
          key={idx}
          style={{
            width,
            height,
            background: 'var(--bg3)',
            borderRadius: '0.375rem',
            animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
            marginBottom: idx < count - 1 ? '0.75rem' : 0,
            ...style,
          }}
        />
      ))}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>
    </>
  );
}
