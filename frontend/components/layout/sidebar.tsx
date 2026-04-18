'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  BookOpen,
  Bot,
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
  const pathname = usePathname();

  const navItems: Array<{ name: string; href: string; icon: LucideIcon }> = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Profile', href: '/profile', icon: User },
    { name: 'Ledger', href: '/bookkeeping', icon: BookOpen },
    { name: 'Transactions', href: '/transactions', icon: CreditCard },
    { name: 'Reports', href: '/reports', icon: FileText },
    { name: 'Deadlines', href: '/deadlines', icon: CalendarDays },
    { name: 'Assistant', href: '/assistant', icon: Bot },
    { name: 'Settings', href: '/settings', icon: Settings },
  ];

  return (
    <aside
      style={{
        width: '280px',
        background: 'var(--bg3)',
        borderRight: '1px solid var(--border)',
        padding: '1.5rem',
        height: '100vh',
        overflowY: 'auto',
        position: 'fixed',
        left: 0,
        top: 0,
        fontWeight: 700,
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
        {navItems.map((item) => {
          const isActive = pathname === item.href || pathname?.startsWith(`${item.href}/`);

          return (
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
                border: isActive ? '1px solid #000000' : '1px solid transparent',
                background: isActive ? 'var(--bg2)' : 'transparent',
              }}
              onMouseEnter={(e) => {
                if (!isActive) e.currentTarget.style.background = 'var(--bg2)';
              }}
              onMouseLeave={(e) => {
                if (!isActive) e.currentTarget.style.background = 'transparent';
              }}
            >
              <span style={{ display: 'inline-flex', alignItems: 'center' }}>
                <item.icon size={18} />
              </span>
              <span style={{ fontSize: '0.95rem', fontWeight: 700 }}>{item.name}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
