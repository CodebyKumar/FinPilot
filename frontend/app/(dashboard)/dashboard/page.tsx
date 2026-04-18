'use client';

import { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, ClipboardList, DollarSign, Download, Lightbulb, Receipt, TrendingUp } from 'lucide-react';
import { PageShell } from '@/components/layout/page-shell';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { apiClient } from '@/lib/api-client';

interface DashboardKpis {
  total_revenue: number;
  total_expenses: number;
  net_profit: number;
  tax_liability: number;
  revenue_trend_pct: number;
  expenses_trend_pct: number;
  profit_trend_pct: number;
  tax_trend_pct: number;
}

interface DashboardTransaction {
  date: string;
  desc: string;
  amount: number;
  type: 'credit' | 'debit';
  status: 'completed' | 'review';
  category?: string;
}

interface DashboardAction {
  title: string;
  priority: 'critical' | 'high' | 'medium' | 'low';
}

interface DashboardMonthlyCluster {
  month: string;
  revenue: number;
  expenses: number;
  profit: number;
}

interface DashboardInsight {
  type?: string;
  text: string;
}

interface DashboardData {
  kpis: DashboardKpis;
  recent_transactions: DashboardTransaction[];
  monthly_clusters: DashboardMonthlyCluster[];
  pending_actions: DashboardAction[];
  ai_insights: DashboardInsight[];
}

const EMPTY_DATA: DashboardData = {
  kpis: {
    total_revenue: 0,
    total_expenses: 0,
    net_profit: 0,
    tax_liability: 0,
    revenue_trend_pct: 0,
    expenses_trend_pct: 0,
    profit_trend_pct: 0,
    tax_trend_pct: 0,
  },
  recent_transactions: [],
  monthly_clusters: [],
  pending_actions: [],
  ai_insights: [],
};

export default function DashboardPage() {
  const userId = 'default';
  const [dashboardData, setDashboardData] = useState<DashboardData>(EMPTY_DATA);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadDashboard = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const response = await apiClient.getDashboardOverview(userId);
        const data = response?.data || response;
        setDashboardData({
          kpis: data?.kpis || EMPTY_DATA.kpis,
          recent_transactions: Array.isArray(data?.recent_transactions) ? data.recent_transactions : [],
          monthly_clusters: Array.isArray(data?.monthly_clusters) ? data.monthly_clusters : [],
          pending_actions: Array.isArray(data?.pending_actions) ? data.pending_actions : [],
          ai_insights: Array.isArray(data?.ai_insights) ? data.ai_insights : [],
        });
      } catch (err: any) {
        setError(err?.response?.data?.detail || err?.message || 'Failed to load dashboard data');
      } finally {
        setIsLoading(false);
      }
    };

    loadDashboard();
  }, [userId]);

  const formatInr = (value: number) =>
    new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    }).format(Number(value || 0));

  const formatTrend = (value: number) => {
    const sign = value > 0 ? '+' : '';
    return `${sign}${Number(value || 0).toFixed(1)}%`;
  };

  const kpiCards = useMemo(
    () => [
      {
        label: 'Total Revenue',
        value: formatInr(dashboardData.kpis.total_revenue),
        trend: formatTrend(dashboardData.kpis.revenue_trend_pct),
        Icon: TrendingUp,
      },
      {
        label: 'Total Expenses',
        value: formatInr(dashboardData.kpis.total_expenses),
        trend: formatTrend(dashboardData.kpis.expenses_trend_pct),
        Icon: Receipt,
      },
      {
        label: 'Net Profit',
        value: formatInr(dashboardData.kpis.net_profit),
        trend: formatTrend(dashboardData.kpis.profit_trend_pct),
        Icon: DollarSign,
      },
      {
        label: 'Tax Liability',
        value: formatInr(dashboardData.kpis.tax_liability),
        trend: formatTrend(dashboardData.kpis.tax_trend_pct),
        Icon: ClipboardList,
      },
    ],
    [dashboardData]
  );

  const maxClusterValue = useMemo(() => {
    const values = dashboardData.monthly_clusters.flatMap((m) => [m.revenue, m.expenses, Math.max(0, m.profit)]);
    const max = Math.max(0, ...values);
    return max > 0 ? max : 1;
  }, [dashboardData.monthly_clusters]);

  return (
    <PageShell
      title="Financial Dashboard"
      subtitle="Overview of your business financials and pending actions"
      headerAction={
        <Button variant="primary">
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.45rem' }}>
            <Download size={16} />
            <span>Upload Statement</span>
          </span>
        </Button>
      }
    >
      {error && (
        <div
          style={{
            marginBottom: '1rem',
            padding: '0.75rem 1rem',
            borderRadius: '0.5rem',
            border: '1px solid var(--rose)',
            color: 'var(--rose)',
            background: 'var(--card-glow-rose)',
          }}
        >
          {error}
        </div>
      )}

      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
        {kpiCards.map((kpi) => (
          <Card key={kpi.label}>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
              <div>
                <p style={{ fontSize: '0.85rem', color: 'var(--muted)', margin: 0 }}>{kpi.label}</p>
                <h3 style={{ fontSize: '1.75rem', fontFamily: 'Syne', fontWeight: 700, margin: '0.5rem 0 0 0' }}>
                  {isLoading ? 'Loading...' : kpi.value}
                </h3>
                <p style={{ fontSize: '0.85rem', color: Number(kpi.trend.replace('%', '')) >= 0 ? 'var(--emerald)' : 'var(--rose)', margin: '0.25rem 0 0 0' }}>
                  {kpi.trend}
                </p>
              </div>
              <div style={{ color: 'var(--muted)', display: 'inline-flex', alignItems: 'center' }}>
                <kpi.Icon size={30} />
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Main Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '2rem' }}>
        {/* Recent Transactions */}
        <Card title="Recent Transactions" subtitle="Latest 5 transactions">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {isLoading ? (
              <p style={{ margin: 0, color: 'var(--muted)' }}>Loading transactions...</p>
            ) : dashboardData.recent_transactions.length === 0 ? (
              <p style={{ margin: 0, color: 'var(--muted)' }}>No transactions found.</p>
            ) : dashboardData.recent_transactions.map((tx, idx) => (
              <div
                key={`${tx.date}-${tx.desc}-${idx}`}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  paddingBottom: '1rem',
                  borderBottom: idx < dashboardData.recent_transactions.length - 1 ? '1px solid var(--border)' : 'none',
                }}
              >
                <div>
                  <p style={{ margin: 0, fontWeight: 600 }}>{tx.desc}</p>
                  <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.85rem', color: 'var(--muted)' }}>
                    {new Date(tx.date).toLocaleDateString()}
                  </p>
                </div>
                <Badge variant={tx.type === 'credit' ? 'success' : 'default'}>
                  {tx.type === 'credit' ? '+' : '-'}{formatInr(tx.amount)}
                </Badge>
              </div>
            ))}
          </div>
        </Card>

        {/* Pending Actions */}
        <Card title="Pending Actions" subtitle="Tasks requiring attention">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {isLoading ? (
              <p style={{ margin: 0, color: 'var(--muted)' }}>Loading actions...</p>
            ) : dashboardData.pending_actions.map((action, idx) => (
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
                <Badge variant={action.priority === 'critical' ? 'error' : action.priority === 'high' ? 'warning' : 'default'}>
                  {action.priority}
                </Badge>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card title="Financial Trend" subtitle="Revenue vs Expenses vs Profit (last 6 months)">
        {isLoading ? (
          <p style={{ margin: 0, color: 'var(--muted)' }}>Preparing graph...</p>
        ) : dashboardData.monthly_clusters.length === 0 ? (
          <p style={{ margin: 0, color: 'var(--muted)' }}>Not enough transaction data to plot trend.</p>
        ) : (
          <>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.82rem', color: 'var(--muted)' }}>
                <span style={{ width: 10, height: 10, borderRadius: 2, background: '#2563eb', display: 'inline-block' }} /> Revenue
              </span>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.82rem', color: 'var(--muted)' }}>
                <span style={{ width: 10, height: 10, borderRadius: 2, background: '#f59e0b', display: 'inline-block' }} /> Expenses
              </span>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.82rem', color: 'var(--muted)' }}>
                <span style={{ width: 10, height: 10, borderRadius: 2, background: '#10b981', display: 'inline-block' }} /> Profit
              </span>
            </div>

            <div style={{
              border: '1px solid var(--border)',
              borderRadius: '0.75rem',
              background: 'linear-gradient(to bottom, rgba(99,102,241,0.04), rgba(0,0,0,0))',
              padding: '1rem 0.75rem 0.75rem',
              overflowX: 'auto',
            }}>
              <div style={{ minWidth: 680, display: 'flex', alignItems: 'flex-end', gap: '0.9rem', height: 260 }}>
                {dashboardData.monthly_clusters.map((bucket, idx) => {
                  const revenueHeight = Math.max(6, Math.round((bucket.revenue / maxClusterValue) * 170));
                  const expensesHeight = Math.max(6, Math.round((bucket.expenses / maxClusterValue) * 170));
                  const profitHeight = Math.max(6, Math.round((Math.max(0, bucket.profit) / maxClusterValue) * 170));

                  const render3DBar = (height: number, front: string, side: string, top: string) => (
                    <div style={{ width: 18, position: 'relative', height, transform: 'skewY(-6deg)' }}>
                      <div style={{ position: 'absolute', inset: 0, background: front, borderRadius: '2px 2px 0 0' }} />
                      <div style={{ position: 'absolute', right: -6, top: 0, width: 6, height, background: side, transform: 'skewY(-45deg)', transformOrigin: 'top left', borderRadius: '0 2px 0 0' }} />
                      <div style={{ position: 'absolute', left: 0, top: -6, width: 18, height: 6, background: top, transform: 'skewX(-45deg)', transformOrigin: 'bottom left', borderRadius: '2px 2px 0 0' }} />
                    </div>
                  );

                  return (
                    <div key={`${bucket.month}-${idx}`} style={{ flex: 1, minWidth: 84, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.55rem' }}>
                      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8, height: 190 }}>
                        {render3DBar(revenueHeight, '#2563eb', '#1d4ed8', '#60a5fa')}
                        {render3DBar(expensesHeight, '#f59e0b', '#d97706', '#fbbf24')}
                        {render3DBar(profitHeight, '#10b981', '#059669', '#34d399')}
                      </div>
                      <div style={{ textAlign: 'center' }}>
                        <p style={{ margin: 0, fontSize: '0.76rem', color: 'var(--muted)' }}>{bucket.month}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </>
        )}
      </Card>

      {/* AI Suggestions */}
      <Card title="AI Insights" subtitle="Smart recommendations from your CFO assistant">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1rem' }}>
          {isLoading ? (
            <p style={{ margin: 0, color: 'var(--muted)' }}>Generating real-time insights...</p>
          ) : dashboardData.ai_insights.length === 0 ? (
            <p style={{ margin: 0, color: 'var(--muted)' }}>No insights available yet.</p>
          ) : dashboardData.ai_insights.map((insight, idx) => {
            const isRisk = insight.type === 'risk';
            const isPerformance = insight.type === 'performance';
            const Icon = isRisk ? AlertTriangle : isPerformance ? TrendingUp : Lightbulb;
            const accent = isRisk ? 'var(--rose)' : isPerformance ? 'var(--emerald)' : 'var(--indigo)';
            const chipBg = isRisk ? 'var(--card-glow-rose)' : isPerformance ? 'var(--card-glow-emerald)' : 'var(--card-glow-indigo)';
            const label = isRisk ? 'Risk Alert' : isPerformance ? 'Performance' : 'Insight';

            return (
            <div
              key={idx}
              style={{
                padding: '1rem',
                background: 'var(--bg3)',
                border: '1px solid var(--border)',
                borderRadius: '0.5rem',
                borderLeft: `4px solid ${accent}`,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.65rem' }}>
                <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.45rem', fontSize: '0.82rem', fontWeight: 700, color: accent, background: chipBg, border: `1px solid ${accent}`, borderRadius: '999px', padding: '0.2rem 0.6rem' }}>
                  <Icon size={14} />
                  <span>{label}</span>
                </div>
                <span style={{ color: 'var(--muted)', fontSize: '0.78rem', fontWeight: 600 }}>Insight {idx + 1}</span>
              </div>
              <p style={{ margin: 0, color: 'var(--text)', lineHeight: 1.55, fontSize: '0.95rem' }}>{insight.text}</p>
            </div>
          );
          })}
        </div>
      </Card>
    </PageShell>
  );
}
