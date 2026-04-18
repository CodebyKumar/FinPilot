'use client';

import { PageShell } from '@/components/layout/page-shell';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

export default function JobsPage() {
  return (
    <PageShell
      title="Jobs & Activity"
      subtitle="Track background tasks and processing status"
    >
      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '1.5rem' }}>
        {[
          { task: 'Statement Parsing', status: 'completed', progress: 100 },
          { task: 'Report Generation', status: 'running', progress: 65 },
          { task: 'Invoice Upload', status: 'pending', progress: 0 },
        ].map((job, idx) => (
          <Card key={idx}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h3 style={{ margin: 0, fontWeight: 600 }}>{job.task}</h3>
              <Badge variant={job.status === 'completed' ? 'success' : job.status === 'running' ? 'info' : 'default'}>
                {job.status}
              </Badge>
            </div>
            <div style={{
              width: '100%',
              height: '8px',
              background: 'var(--bg3)',
              borderRadius: '4px',
              overflow: 'hidden',
            }}>
              <div style={{
                height: '100%',
                background: job.status === 'completed' ? 'var(--emerald)' : 'var(--indigo)',
                width: `${job.progress}%`,
                transition: 'width 0.3s ease',
              }} />
            </div>
            <p style={{ margin: '0.5rem 0 0 0', fontSize: '0.85rem', color: 'var(--muted)' }}>
              {job.progress}% Complete
            </p>
          </Card>
        ))}
      </div>
    </PageShell>
  );
}
