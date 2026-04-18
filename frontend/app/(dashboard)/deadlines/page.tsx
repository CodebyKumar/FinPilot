'use client';

import { useEffect, useMemo, useState } from 'react';
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
      setMessage('Deadline saved successfully.', 'success');
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
                  <p style={{ margin: '0.5rem 0 0 0', color: 'var(--muted)', fontSize: '0.9rem' }}>
                    📅 {deadline.due_date} • {deadline.type}
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
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  {deadline.meta?.source === 'bookkeeping_invoice_upload' && (
                    <Badge variant="info">Auto from invoice</Badge>
                  )}
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
