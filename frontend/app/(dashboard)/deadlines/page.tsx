'use client';

import { useEffect, useMemo, useState } from 'react';
import { CalendarDays } from 'lucide-react';
import { PageShell } from '@/components/layout/page-shell';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { apiClient } from '@/lib/api-client';

interface DeadlineItem {
  deadline_id: string;
  title: string;
  due_date: string;
  type: string;
  status: string;
  submitted?: boolean;
  meta?: Record<string, any>;
  created_at?: string;
  updated_at?: string;
}

const EMPTY_FORM = {
  title: '',
  dueDate: '',
  type: 'compliance',
  status: 'pending',
};

export default function DeadlinesPage() {
  const userId = 'default';

  const [deadlines, setDeadlines] = useState<DeadlineItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isSendingReminders, setIsSendingReminders] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [viewMonth, setViewMonth] = useState(() => {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), 1);
  });
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [statusType, setStatusType] = useState<'success' | 'error' | 'info' | null>(null);

  const setMessage = (message: string, type: 'success' | 'error' | 'info') => {
    setStatusMessage(message);
    setStatusType(type);
  };

  const getErrorMessage = (error: unknown, fallback: string) => {
    const maybeAxios = error as {
      response?: { data?: { detail?: string } };
      message?: string;
    };
    return maybeAxios?.response?.data?.detail || maybeAxios?.message || fallback;
  };

  const loadDeadlines = async () => {
    try {
      setIsLoading(true);
      const response = await apiClient.getDeadlines(userId);
      const payload = response?.data || response;
      const data = payload?.data || payload;
      setDeadlines(Array.isArray(data?.deadlines) ? data.deadlines : []);
    } catch (error) {
      setMessage(getErrorMessage(error, 'Failed to load deadlines'), 'error');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void loadDeadlines();
    const intervalId = window.setInterval(() => {
      void loadDeadlines();
    }, 15000);

    return () => window.clearInterval(intervalId);
  }, []);

  const filteredDeadlines = useMemo(() => {
    return [...deadlines].sort((a, b) => new Date(a.due_date).getTime() - new Date(b.due_date).getTime());
  }, [deadlines]);

  const formatDateKey = (raw: string | Date) => {
    const d = typeof raw === 'string' ? new Date(raw) : raw;
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  };

  const deadlineDateMap = useMemo(() => {
    const map = new Map<string, DeadlineItem[]>();
    for (const item of filteredDeadlines) {
      const key = formatDateKey(item.due_date);
      const existing = map.get(key) || [];
      existing.push(item);
      map.set(key, existing);
    }
    return map;
  }, [filteredDeadlines]);

  const monthCells = useMemo(() => {
    const start = new Date(viewMonth.getFullYear(), viewMonth.getMonth(), 1);
    const monthStartDay = start.getDay();
    const gridStart = new Date(start);
    gridStart.setDate(start.getDate() - monthStartDay);

    return Array.from({ length: 42 }).map((_, idx) => {
      const date = new Date(gridStart);
      date.setDate(gridStart.getDate() + idx);
      const key = formatDateKey(date);
      const items = deadlineDateMap.get(key) || [];
      return {
        date,
        key,
        inMonth: date.getMonth() === viewMonth.getMonth(),
        items,
      };
    });
  }, [viewMonth, deadlineDateMap]);

  const handleSaveDeadline = async () => {
    if (!form.title.trim() || !form.dueDate) {
      setMessage('Title and due date are required.', 'error');
      return;
    }

    try {
      setIsSaving(true);
      await apiClient.addDeadline({
        user_id: userId,
        title: form.title.trim(),
        due_date: form.dueDate,
        type: form.type,
        status: form.status,
        submitted: false,
        meta: {},
      });
      setForm(EMPTY_FORM);
      setMessage('Deadline detected and reminder email triggered.', 'success');
      await loadDeadlines();
    } catch (error) {
      setMessage(getErrorMessage(error, 'Failed to save deadline'), 'error');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteDeadline = async (deadlineId: string) => {
    try {
      await apiClient.deleteDeadline(deadlineId, userId);
      setMessage('Deadline deleted.', 'success');
      await loadDeadlines();
    } catch (error) {
      setMessage(getErrorMessage(error, 'Failed to delete deadline'), 'error');
    }
  };

  const handleSendReminders = async () => {
    try {
      setIsSendingReminders(true);
      const response = await apiClient.sendDeadlineReminders(userId);
      const payload = response?.data || response;
      const data = payload?.data || payload;
      setMessage(
        `Reminders queued: ${data?.queued_new ?? 0}, sent: ${data?.sent ?? 0}, still queued: ${data?.still_queued ?? 0}`,
        'success'
      );
      await loadDeadlines();
    } catch (error) {
      setMessage(getErrorMessage(error, 'Failed to send reminders'), 'error');
    } finally {
      setIsSendingReminders(false);
    }
  };

  return (
    <PageShell
      title="Deadlines & Compliance"
      subtitle="Track important dates and compliance requirements"
    >
      {statusMessage && statusType && (
        <div
          style={{
            marginBottom: '1rem',
            padding: '0.75rem 1rem',
            borderRadius: '0.5rem',
            border: `1px solid ${statusType === 'success' ? 'var(--emerald)' : statusType === 'error' ? 'var(--rose)' : 'var(--border)'}`,
            color: statusType === 'success' ? 'var(--emerald)' : statusType === 'error' ? 'var(--rose)' : 'var(--text)',
            background: statusType === 'success' ? 'var(--card-glow-emerald)' : statusType === 'error' ? 'rgba(244, 63, 94, 0.08)' : 'var(--bg2)',
          }}
        >
          {statusMessage}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '1.5rem' }}>
        <Card title="Add Deadline" subtitle="Create a new compliance reminder">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <Input
              label="Title"
              placeholder="e.g. GST Return"
              value={form.title}
              onChange={(e) => setForm((prev) => ({ ...prev, title: e.target.value }))}
              disabled={isSaving}
            />
            <Input
              label="Due Date"
              type="date"
              value={form.dueDate}
              onChange={(e) => setForm((prev) => ({ ...prev, dueDate: e.target.value }))}
              disabled={isSaving}
            />
            <Input
              label="Type"
              value={form.type}
              onChange={(e) => setForm((prev) => ({ ...prev, type: e.target.value }))}
              disabled={isSaving}
              placeholder="compliance / tax / gst / payment"
            />
            <Input
              label="Status"
              value={form.status}
              onChange={(e) => setForm((prev) => ({ ...prev, status: e.target.value }))}
              disabled={isSaving}
              placeholder="pending / upcoming / submitted / overdue"
            />
            <Button variant="primary" onClick={handleSaveDeadline} disabled={isSaving}>
              {isSaving ? 'Saving...' : 'Save Deadline'}
            </Button>
          </div>
        </Card>

        <Card title="Actions" subtitle="Sync reminders and refresh live deadlines">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{ padding: '1rem', borderRadius: '0.5rem', background: 'var(--bg3)' }}>
              <strong>{filteredDeadlines.length}</strong> deadlines loaded
            </div>
            <Button variant="secondary" onClick={() => void loadDeadlines()} disabled={isLoading}>
              {isLoading ? 'Refreshing...' : 'Refresh Deadlines'}
            </Button>
            <Button variant="success" onClick={handleSendReminders} disabled={isSendingReminders}>
              {isSendingReminders ? 'Sending...' : 'Send Deadline Reminders'}
            </Button>
          </div>
        </Card>
      </div>

      <Card
        title="Deadline Calendar"
        subtitle="Highlighted dates indicate reminder/deadline entries"
        style={{ marginBottom: '1.5rem' }}
      >
        <div style={{ maxWidth: '900px', margin: '0 auto' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
          <Button
            variant="secondary"
            onClick={() => setViewMonth((prev) => new Date(prev.getFullYear(), prev.getMonth() - 1, 1))}
          >
            Previous
          </Button>
          <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700 }}>
            {viewMonth.toLocaleDateString('en-IN', { month: 'long', year: 'numeric' })}
          </h3>
          <Button
            variant="secondary"
            onClick={() => setViewMonth((prev) => new Date(prev.getFullYear(), prev.getMonth() + 1, 1))}
          >
            Next
          </Button>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, minmax(0, 1fr))', gap: '0.35rem', marginBottom: '0.35rem' }}>
          {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day) => (
            <div key={day} style={{ textAlign: 'center', fontSize: '0.75rem', color: 'var(--muted)', fontWeight: 700 }}>
              {day}
            </div>
          ))}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, minmax(0, 1fr))', gap: '0.35rem' }}>
          {monthCells.map((cell) => {
            const hasReminder = cell.items.length > 0;
            const isToday = formatDateKey(new Date()) === cell.key;
            const hasOverdue = cell.items.some((d) => d.status === 'overdue');
            const accent = hasOverdue ? 'var(--rose)' : 'var(--amber)';

            return (
              <div
                key={cell.key}
                style={{
                  minHeight: '68px',
                  borderRadius: '0.5rem',
                  border: `1px solid ${hasReminder ? accent : 'var(--border)'}`,
                  background: hasReminder ? 'var(--card-glow-amber)' : 'var(--bg2)',
                  padding: '0.35rem 0.4rem',
                  opacity: cell.inMonth ? 1 : 0.55,
                  boxShadow: isToday ? '0 0 0 2px rgba(99, 102, 241, 0.22)' : 'none',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.2rem' }}>
                  <span style={{ fontSize: '0.72rem', fontWeight: 700 }}>{cell.date.getDate()}</span>
                  {hasReminder && (
                    <span style={{ fontSize: '0.68rem', color: accent, fontWeight: 700 }}>
                      {cell.items.length}
                    </span>
                  )}
                </div>

                {hasReminder && (
                  <div style={{ display: 'grid', gap: '0.2rem' }}>
                    {cell.items.slice(0, 1).map((d) => (
                      <div
                        key={d.deadline_id}
                        style={{
                          fontSize: '0.66rem',
                          color: 'var(--text)',
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                        }}
                        title={d.title}
                      >
                        • {d.title}
                      </div>
                    ))}
                    {cell.items.length > 1 && (
                      <div style={{ fontSize: '0.64rem', color: 'var(--muted)' }}>+{cell.items.length - 1} more</div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
        </div>
      </Card>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '1.5rem' }}>
        {isLoading ? (
          <Card>
            <p style={{ margin: 0, color: 'var(--muted)' }}>Loading deadlines...</p>
          </Card>
        ) : filteredDeadlines.length === 0 ? (
          <Card>
            <p style={{ margin: 0, color: 'var(--muted)' }}>No deadlines found. Add one above to get started.</p>
          </Card>
        ) : (
          filteredDeadlines.map((deadline) => (
            <Card key={deadline.deadline_id}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem' }}>
                <div>
                  <h3 style={{ fontSize: '1.1rem', fontWeight: 600, margin: 0 }}>{deadline.title}</h3>
                  <p style={{ margin: '0.5rem 0 0 0', color: 'var(--muted)', fontSize: '0.9rem', display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}>
                    <CalendarDays size={14} />
                    <span>{deadline.due_date} • {deadline.type}</span>
                  </p>
                  {deadline.meta?.financial_year_end && (
                    <p style={{ margin: '0.35rem 0 0 0', color: 'var(--muted)', fontSize: '0.85rem' }}>
                      FY end: {deadline.meta.financial_year_end}
                    </p>
                  )}
                  {deadline.meta?.invoice_date && (
                    <p style={{ margin: '0.35rem 0 0 0', color: 'var(--muted)', fontSize: '0.85rem' }}>
                      Invoice date: {deadline.meta.invoice_date}
                    </p>
                  )}
                  {deadline.meta?.transaction_date && (
                    <p style={{ margin: '0.35rem 0 0 0', color: 'var(--muted)', fontSize: '0.85rem' }}>
                      Transaction date: {deadline.meta.transaction_date}
                    </p>
                  )}
                  {deadline.meta?.transaction_month && (
                    <p style={{ margin: '0.35rem 0 0 0', color: 'var(--muted)', fontSize: '0.85rem' }}>
                      Transaction month: {String(deadline.meta.transaction_month)}
                    </p>
                  )}
                  {deadline.meta?.amount !== undefined && (
                    <p style={{ margin: '0.35rem 0 0 0', color: 'var(--muted)', fontSize: '0.85rem' }}>
                      Amount: ₹{Number(deadline.meta.amount || 0).toLocaleString('en-IN')}
                      {deadline.meta?.transaction_type ? ` • ${String(deadline.meta.transaction_type)}` : ''}
                    </p>
                  )}
                  {deadline.meta?.party && deadline.meta?.source === 'transaction_auto_deadline' && (
                    <p style={{ margin: '0.35rem 0 0 0', color: 'var(--muted)', fontSize: '0.85rem' }}>
                      Party: {String(deadline.meta.party)}
                    </p>
                  )}
                  {deadline.meta?.category && deadline.meta?.source === 'transaction_auto_deadline' && (
                    <p style={{ margin: '0.35rem 0 0 0', color: 'var(--muted)', fontSize: '0.85rem' }}>
                      Category: {String(deadline.meta.category)}
                      {deadline.meta?.sub_category ? ` / ${String(deadline.meta.sub_category)}` : ''}
                    </p>
                  )}
                  {deadline.meta?.reminder_status && (
                    <p style={{ margin: '0.35rem 0 0 0', color: deadline.meta.reminder_status === 'sent' ? 'var(--emerald)' : deadline.meta.reminder_status === 'failed' ? 'var(--rose)' : 'var(--muted)', fontSize: '0.85rem' }}>
                      Reminder email: {String(deadline.meta.reminder_status)}
                      {deadline.meta?.reminder_sent_at ? ` (${new Date(String(deadline.meta.reminder_sent_at)).toLocaleString()})` : ''}
                    </p>
                  )}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  {deadline.meta?.source === 'bookkeeping_invoice_upload' && (
                    <Badge variant="info">Auto from invoice</Badge>
                  )}
                  {deadline.meta?.source === 'transaction_auto_deadline' && (
                    <Badge variant="info">Auto from transaction</Badge>
                  )}
                  {deadline.meta?.reminder_status === 'sent' && <Badge variant="success">Email sent</Badge>}
                  {deadline.meta?.reminder_status === 'failed' && <Badge variant="error">Email failed</Badge>}
                  {deadline.meta?.reminder_status === 'queued' && <Badge variant="warning">Email queued</Badge>}
                  <Badge variant={deadline.status === 'pending' ? 'warning' : deadline.status === 'overdue' ? 'error' : 'info'}>
                    {deadline.status}
                  </Badge>
                  <Button variant="danger" onClick={() => void handleDeleteDeadline(deadline.deadline_id)}>
                    Delete
                  </Button>
                </div>
              </div>
            </Card>
          ))
        )}
      </div>
    </PageShell>
  );
}
