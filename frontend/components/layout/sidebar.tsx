'use client';

import Link from 'next/link';

export function Sidebar() {
  const navItems = [
    { name: 'Dashboard', href: '/dashboard', icon: '📊' },
    { name: 'Profile', href: '/profile', icon: '👤' },
    { name: 'Bookkeeping', href: '/bookkeeping', icon: '📖' },
    { name: 'Transactions', href: '/transactions', icon: '💳' },
    { name: 'Reports', href: '/reports', icon: '📋' },
    { name: 'Deadlines', href: '/deadlines', icon: '📅' },
    { name: 'Assistant', href: '/assistant', icon: '🤖' },
    { name: 'Jobs', href: '/jobs', icon: '⚙️' },
    { name: 'Settings', href: '/settings', icon: '⚙️' },
  ];

  return (
    <aside
      style={{
        width: '280px',
        background: 'var(--bg2)',
        borderRight: '1px solid var(--border)',
        padding: '1.5rem',
        height: '100vh',
        overflowY: 'auto',
        position: 'fixed',
        left: 0,
        top: 0,
      }}
    >
      <Link href="/" style={{ textDecoration: 'none' }}>
        <div style={{
          fontSize: '1.5rem',
          fontFamily: 'Syne',
          fontWeight: 700,
          color: 'var(--indigo)',
          marginBottom: '2rem',
        }}>
          💰 FinPilot
        </div>
      </Link>

      <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
              padding: '0.75rem 1rem',
              borderRadius: '0.5rem',
              color: 'var(--text)',
              textDecoration: 'none',
              transition: 'all 0.2s ease',
            }}
            onMouseEnter={(e) => e.currentTarget.style.background = 'var(--bg3)'}
            onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
          >
            <span>{item.icon}</span>
            <span style={{ fontSize: '0.95rem' }}>{item.name}</span>
          </Link>
        ))}
      </nav>
    </aside>
  );
}
