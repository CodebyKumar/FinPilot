'use client';

import { PageShell } from '@/components/layout/page-shell';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

export default function SettingsPage() {
  return (
    <PageShell
      title="Settings"
      subtitle="Configure your preferences and application settings"
    >
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
                <option>Dark (Default)</option>
                <option>Light</option>
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
            <Button variant="danger">Delete Account</Button>
          </div>
        </Card>
      </div>
    </PageShell>
  );
}
