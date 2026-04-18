'use client';

import { ReactNode, CSSProperties } from 'react';

interface ModalProps {
  isOpen: boolean;
  title: string;
  children: ReactNode;
  onClose: () => void;
  footer?: ReactNode;
  size?: 'sm' | 'md' | 'lg';
}

export function Modal({ isOpen, title, children, onClose, footer, size = 'md' }: ModalProps) {
  if (!isOpen) return null;

  const sizes: Record<string, string> = {
    sm: '400px',
    md: '600px',
    lg: '900px',
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0, 0, 0, 0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 50,
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: 'var(--bg2)',
          border: '1px solid var(--border)',
          borderRadius: '0.75rem',
          width: '90%',
          maxWidth: sizes[size],
          maxHeight: '90vh',
          overflow: 'auto',
          display: 'flex',
          flexDirection: 'column',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '1.5rem',
            borderBottom: '1px solid var(--border)',
          }}
        >
          <h2 style={{ fontSize: '1.25rem', fontFamily: 'Syne', margin: 0 }}>
            {title}
          </h2>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--muted)',
              fontSize: '1.5rem',
              cursor: 'pointer',
            }}
          >
            ×
          </button>
        </div>
        <div style={{ flex: 1, padding: '1.5rem', overflow: 'auto' }}>
          {children}
        </div>
        {footer && (
          <div
            style={{
              display: 'flex',
              gap: '1rem',
              padding: '1.5rem',
              borderTop: '1px solid var(--border)',
              justifyContent: 'flex-end',
            }}
          >
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
