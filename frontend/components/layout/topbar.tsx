'use client';

import { Bell, User } from 'lucide-react';

export function Topbar() {
  return (
    <header
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '1rem 2rem',
        background: 'rgba(255, 255, 255, 0.9)',
        borderBottom: '1px solid var(--border)',
        position: 'sticky',
        top: 0,
        zIndex: 40,
        backdropFilter: 'blur(10px)',
      }}
    >
      <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flex: 1 }}>
        <input
          type="text"
          placeholder="Search..."
          style={{
            padding: '0.5rem 1rem',
            background: 'var(--bg3)',
            border: '1px solid var(--border)',
            borderRadius: '0.5rem',
            color: 'var(--text)',
            width: '250px',
          }}
        />
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <button
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--text)',
            cursor: 'pointer',
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Bell size={20} />
        </button>
        <button
          style={{
            background: 'var(--indigo)',
            border: 'none',
            borderRadius: '50%',
            width: '40px',
            height: '40px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white',
          }}
        >
          <User size={18} />
        </button>
      </div>
    </header>
  );
}
