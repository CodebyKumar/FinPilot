'use client';

import { PageShell } from '@/components/layout/page-shell';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

export default function DeadlinesPage() {
  return (
    <PageShell
      title="Deadlines & Compliance"
      subtitle="Track important dates and compliance requirements"
    >
      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '1.5rem' }}>
        {[
          { title: 'ITR Filing Deadline', date: '2024-02-28', type: 'tax_filing', status: 'pending' },
          { title: 'GST Return (Feb)', date: '2024-02-20', type: 'gst_filing', status: 'pending' },
          { title: 'Quarterly Payment', date: '2024-03-15', type: 'payment', status: 'upcoming' },
        ].map((deadline, idx) => (
          <Card key={idx}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h3 style={{ fontSize: '1.1rem', fontWeight: 600, margin: 0 }}>{deadline.title}</h3>
                <p style={{ margin: '0.5rem 0 0 0', color: 'var(--muted)', fontSize: '0.9rem' }}>
                  📅 {deadline.date}
                </p>
              </div>
              <Badge variant={deadline.status === 'pending' ? 'warning' : 'info'}>
                {deadline.status}
              </Badge>
            </div>
          </Card>
        ))}
      </div>
    </PageShell>
  );
}
