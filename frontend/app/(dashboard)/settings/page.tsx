'use client';

import { useState } from 'react';
import { PageShell } from '@/components/layout/page-shell';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { apiClient } from '@/lib/api-client';

export default function SettingsPage() {
  const userId = 'default';
  const [isDeleting, setIsDeleting] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [statusType, setStatusType] = useState<'success' | 'error' | null>(null);

  const getErrorMessage = (error: unknown, fallback: string) => {
    const maybeAxios = error as {
      response?: { data?: { detail?: string } };
      message?: string;
    };
    return maybeAxios?.response?.data?.detail || maybeAxios?.message || fallback;
  };

  const handleDeleteAccount = async () => {
    const confirmed = window.confirm('Are you sure you want to delete your account profile? This action cannot be undone.');
    if (!confirmed) return;

    try {
      setIsDeleting(true);
      const response = await apiClient.deleteProfile(userId);
      const payload = response?.data || response;
      const data = payload?.data || payload;

      if (data?.deleted) {
        setStatusMessage('Account profile deleted successfully.');
        setStatusType('success');
      } else {
        setStatusMessage(data?.error || 'No active account profile found to delete.');
        setStatusType('error');
      }
    } catch (error) {
      setStatusMessage(getErrorMessage(error, 'Failed to delete account profile'));
      setStatusType('error');
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <PageShell
      title="Settings"
      subtitle="Configure your preferences and application settings"
    >
      {statusMessage && statusType && (
        <div
          style={{
            marginBottom: '1rem',
            padding: '0.75rem 1rem',
            borderRadius: '0.5rem',
            border: `1px solid ${statusType === 'success' ? 'var(--emerald)' : 'var(--rose)'}`,
            color: statusType === 'success' ? 'var(--emerald)' : 'var(--rose)',
            background: statusType === 'success' ? 'var(--card-glow-emerald)' : 'rgba(244, 63, 94, 0.08)',
          }}
        >
          {statusMessage}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
        <Card title="Notifications">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
              <input type="checkbox" defaultChecked />
              <span>Email Reminders</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
              <input type="checkbox" defaultChecked />
              <span>SMS Alerts</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
              <input type="checkbox" />
              <span>Weekly Digest</span>
            </label>
            <Button variant="primary">Save Preferences</Button>
          </div>
        </Card>

        <Card title="Appearance">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div>
              <label style={{ fontSize: '0.9rem', fontWeight: 600, display: 'block', marginBottom: '0.5rem' }}>Theme</label>
              <select style={{
                width: '100%',
                padding: '0.5rem',
                background: 'var(--bg3)',
                border: '1px solid var(--border)',
                borderRadius: '0.5rem',
                color: 'var(--text)',
              }}>
                <option>Light (Default)</option>
                <option>Dark</option>
              </select>
            </div>
            <Button variant="primary">Save Changes</Button>
          </div>
        </Card>

        <Card title="Security" style={{ gridColumn: '1 / -1' }}>
          <div style={{ display: 'flex', gap: '1rem' }}>
            <Input type="password" placeholder="Current Password" />
            <Input type="password" placeholder="New Password" />
            <Input type="password" placeholder="Confirm Password" />
            <Button variant="primary">Change Password</Button>
          </div>
        </Card>

        <Card title="Account" style={{ gridColumn: '1 / -1' }}>
          <div style={{ padding: '1rem', background: 'var(--card-glow-rose)', borderRadius: '0.5rem', borderLeft: '3px solid var(--rose)' }}>
            <p style={{ margin: 0, color: 'var(--text)', marginBottom: '1rem' }}>Danger Zone - Irreversible Actions</p>
            <Button variant="danger" onClick={handleDeleteAccount} disabled={isDeleting}>
              {isDeleting ? 'Deleting...' : 'Delete Account'}
            </Button>
          </div>
        </Card>
      </div>
    </PageShell>
  );
}
