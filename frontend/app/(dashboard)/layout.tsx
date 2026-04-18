import { ReactNode } from 'react';
import { Sidebar } from '@/components/layout/sidebar';
import { Topbar } from '@/components/layout/topbar';

export default function DashboardLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      <Sidebar />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', marginLeft: '280px' }}>
        <Topbar />
        <main
          style={{
            flex: 1,
            overflow: 'auto',
            padding: '2rem',
            background: 'var(--bg)',
          }}
        >
          {children}
        </main>
      </div>
    </div>
  );
}
