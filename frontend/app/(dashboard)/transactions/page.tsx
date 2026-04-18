'use client';

import { useEffect, useMemo, useState } from 'react';
import { PageShell } from '@/components/layout/page-shell';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { apiClient } from '@/lib/api-client';

interface LedgerEntry {
  date: string;
  party: string;
  type: 'credit' | 'debit';
  amount: number;
  category?: string;
  confidence?: number;
}

export default function TransactionsPage() {
  const userId = 'default';

  const [entries, setEntries] = useState<LedgerEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');

  useEffect(() => {
    const loadEntries = async () => {
      try {
        setIsLoading(true);
        const response = await apiClient.getBookkeepingLedger(userId);
        const data = response?.data;
        const ledgerEntries = Array.isArray(data?.entries) ? (data.entries as LedgerEntry[]) : [];
        setEntries(ledgerEntries);
      } finally {
        setIsLoading(false);
      }
    };

    loadEntries();
  }, [userId]);

  const filteredEntries = useMemo(() => {
    const searchText = search.trim().toLowerCase();
    const fromTs = fromDate ? new Date(fromDate).getTime() : null;
    const toTs = toDate ? new Date(toDate).getTime() : null;

    return entries
      .filter((entry) => {
        const entryTime = new Date(entry.date).getTime();
        const matchesSearch =
          !searchText ||
          entry.party.toLowerCase().includes(searchText) ||
          (entry.category || '').toLowerCase().includes(searchText);
        const matchesFrom = fromTs === null || entryTime >= fromTs;
        const matchesTo = toTs === null || entryTime <= toTs + 24 * 60 * 60 * 1000 - 1;
        return matchesSearch && matchesFrom && matchesTo;
      })
      .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
  }, [entries, search, fromDate, toDate]);

  return (
    <PageShell
      title="Transactions"
      subtitle="View and manage all transactions"
    >
      <Card>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem', marginBottom: '2rem' }}>
          <Input
            placeholder="Search by party or category"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <Input
            type="date"
            placeholder="From date"
            value={fromDate}
            onChange={(e) => setFromDate(e.target.value)}
          />
          <Input
            type="date"
            placeholder="To date"
            value={toDate}
            onChange={(e) => setToDate(e.target.value)}
          />
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{
            width: '100%',
            borderCollapse: 'collapse',
            textAlign: 'left',
            fontSize: '0.95rem',
          }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                <th style={{ padding: '1rem', fontWeight: 600 }}>Date</th>
                <th style={{ padding: '1rem', fontWeight: 600 }}>Description</th>
                <th style={{ padding: '1rem', fontWeight: 600 }}>Category</th>
                <th style={{ padding: '1rem', fontWeight: 600 }}>Amount</th>
                <th style={{ padding: '1rem', fontWeight: 600 }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={5} style={{ padding: '1rem', color: 'var(--muted)' }}>Loading transactions...</td>
                </tr>
              ) : filteredEntries.length === 0 ? (
                <tr>
                  <td colSpan={5} style={{ padding: '1rem', color: 'var(--muted)' }}>No parsed transactions found.</td>
                </tr>
              ) : (
                filteredEntries.map((entry, idx) => {
                  const amountText = `${entry.type === 'credit' ? '+' : '-'}₹${Number(entry.amount || 0).toFixed(2)}`;
                  const confidence = Number(entry.confidence ?? 0);
                  const status: 'success' | 'warning' = confidence >= 0.7 ? 'success' : 'warning';

                  return (
                    <tr key={`${entry.date}-${entry.party}-${idx}`} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td style={{ padding: '1rem' }}>{new Date(entry.date).toLocaleDateString()}</td>
                      <td style={{ padding: '1rem' }}>{entry.party || 'Unknown'}</td>
                      <td style={{ padding: '1rem' }}>{entry.category || 'Uncategorized'}</td>
                      <td style={{ padding: '1rem', color: entry.type === 'credit' ? 'var(--emerald)' : 'var(--text)' }}>{amountText}</td>
                      <td style={{ padding: '1rem' }}>
                        <Badge variant={status}>
                          {confidence >= 0.7 ? 'parsed' : 'review'}
                        </Badge>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </PageShell>
  );
}
