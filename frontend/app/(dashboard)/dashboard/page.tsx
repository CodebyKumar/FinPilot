'use client';

import { PageShell } from '@/components/layout/page-shell';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

export default function DashboardPage() {
  return (
    <PageShell
      title="Financial Dashboard"
      subtitle="Overview of your business financials and pending actions"
      headerAction={
        <Button variant="primary">📥 Upload Statement</Button>
      }
    >
      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
        {[
          { label: 'Total Revenue', value: '₹5,42,500', trend: '+12%', icon: '📈' },
          { label: 'Total Expenses', value: '₹2,10,300', trend: '+5%', icon: '💸' },
          { label: 'Net Profit', value: '₹3,32,200', trend: '+18%', icon: '💰' },
          { label: 'Tax Liability', value: '₹49,830', trend: '-8%', icon: '📋' },
        ].map((kpi) => (
          <Card key={kpi.label}>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
              <div>
                <p style={{ fontSize: '0.85rem', color: 'var(--muted)', margin: 0 }}>{kpi.label}</p>
                <h3 style={{ fontSize: '1.75rem', fontFamily: 'Syne', fontWeight: 700, margin: '0.5rem 0 0 0' }}>
                  {kpi.value}
                </h3>
                <p style={{ fontSize: '0.85rem', color: 'var(--emerald)', margin: '0.25rem 0 0 0' }}>
                  {kpi.trend}
                </p>
              </div>
              <div style={{ fontSize: '2rem' }}>{kpi.icon}</div>
            </div>
          </Card>
        ))}
      </div>

      {/* Main Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '2rem' }}>
        {/* Recent Transactions */}
        <Card title="Recent Transactions" subtitle="Latest 5 transactions">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {[
              { date: 'Today', desc: 'Office Supplies Purchase', amount: '-₹1,250', status: 'completed' },
              { date: 'Yesterday', desc: 'Client Invoice Payment', amount: '+₹15,000', status: 'completed' },
              { date: '2 days ago', desc: 'Utility Bill', amount: '-₹5,500', status: 'pending' },
            ].map((tx, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  paddingBottom: '1rem',
                  borderBottom: idx < 2 ? '1px solid var(--border)' : 'none',
                }}
              >
                <div>
                  <p style={{ margin: 0, fontWeight: 600 }}>{tx.desc}</p>
                  <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.85rem', color: 'var(--muted)' }}>{tx.date}</p>
                </div>
                <Badge variant={tx.amount.startsWith('+') ? 'success' : 'default'}>
                  {tx.amount}
                </Badge>
              </div>
            ))}
          </div>
        </Card>

        {/* Pending Actions */}
        <Card title="Pending Actions" subtitle="Tasks requiring attention">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {[
              { title: 'Complete Profile', priority: 'high' },
              { title: 'Upload GST Returns', priority: 'critical' },
              { title: 'Review Pending Invoices', priority: 'medium' },
            ].map((action, idx) => (
              <div
                key={idx}
                style={{
                  padding: '1rem',
                  background: 'var(--bg3)',
                  borderRadius: '0.5rem',
                  border: `1px solid var(--${action.priority === 'critical' ? 'rose' : action.priority === 'high' ? 'amber' : 'border'})`,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <p style={{ margin: 0, fontWeight: 500 }}>{action.title}</p>
                <Badge variant={action.priority === 'critical' ? 'error' : 'warning'}>
                  {action.priority}
                </Badge>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* AI Suggestions */}
      <Card title="AI Insights" subtitle="Smart recommendations from your CFO assistant">
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {[
            '💡 Your office supplies expense increased by 25% this month. Consider bulk purchasing to reduce costs.',
            '📊 Current tax savings potential: ₹18,500. Review Section 80C investments.',
            '⚠️ 3 invoices from May are still unpaid. Send reminders to maintain cash flow.',
          ].map((insight, idx) => (
            <div
              key={idx}
              style={{
                padding: '1rem',
                background: 'var(--card-glow-indigo)',
                borderRadius: '0.5rem',
                borderLeft: '3px solid var(--indigo)',
              }}
            >
              <p style={{ margin: 0, color: 'var(--text)' }}>{insight}</p>
            </div>
          ))}
        </div>
      </Card>
    </PageShell>
  );
}
