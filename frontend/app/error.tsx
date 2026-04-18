'use client';

import { useEffect } from 'react';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100vh',
      background: 'var(--bg)',
      color: 'var(--text)',
      flexDirection: 'column',
      gap: '1.5rem',
    }}>
      <div style={{ textAlign: 'center' }}>
        <h2 style={{ fontSize: '1.5rem', fontFamily: 'Syne', marginBottom: '0.5rem', color: 'var(--rose)' }}>
          Something went wrong
        </h2>
        <p style={{ color: 'var(--muted)', marginBottom: '1rem' }}>
          {error.message || 'An unexpected error occurred'}
        </p>
      </div>
      <button
        onClick={reset}
        style={{
          padding: '0.75rem 1.5rem',
          background: 'var(--indigo)',
          color: 'white',
          border: 'none',
          borderRadius: '0.5rem',
          cursor: 'pointer',
          fontWeight: 600,
        }}
      >
        Try again
      </button>
    </div>
  );
}
