'use client';

import Link from 'next/link';
import {
  BookOpen,
  Bot,
  Briefcase,
  CalendarDays,
  CreditCard,
  FileText,
  LayoutDashboard,
  Settings,
  User,
  Wallet,
  type LucideIcon,
} from 'lucide-react';

export function Sidebar() {
  const navItems: Array<{ name: string; href: string; icon: LucideIcon }> = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Profile', href: '/profile', icon: User },
    { name: 'Bookkeeping', href: '/bookkeeping', icon: BookOpen },
    { name: 'Transactions', href: '/transactions', icon: CreditCard },
    { name: 'Reports', href: '/reports', icon: FileText },
    { name: 'Deadlines', href: '/deadlines', icon: CalendarDays },
    { name: 'Assistant', href: '/assistant', icon: Bot },
    { name: 'Jobs', href: '/jobs', icon: Briefcase },
    { name: 'Settings', href: '/settings', icon: Settings },
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
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.5rem',
        }}>
          <Wallet size={22} />
          <span>FinPilot</span>
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
            <span style={{ display: 'inline-flex', alignItems: 'center' }}>
              <item.icon size={18} />
            </span>
            <span style={{ fontSize: '0.95rem' }}>{item.name}</span>
          </Link>
        ))}
      </nav>
    </aside>
  );
}
