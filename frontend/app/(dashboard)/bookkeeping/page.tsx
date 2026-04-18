'use client';

import { useEffect, useRef, useState, type ChangeEvent } from 'react';
import { PageShell } from '@/components/layout/page-shell';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { apiClient } from '@/lib/api-client';

interface BookkeepingEntry {
  date: string;
  party: string;
  type: 'credit' | 'debit';
  amount: number;
  category?: string;
  gst_amount?: number;
  running_balance?: number;
  confidence?: number;
}

interface BalanceSummary {
  total_credits: number;
  total_debits: number;
  net_cash_flow: number;
  total_gst_paid: number;
  total_itc_claimable: number;
  transaction_count: number;
  category_counts?: Record<string, number>;
  insights?: string[];
  action_items?: Array<{ message: string }>;
}

interface BookkeepingSummary {
  entries: BookkeepingEntry[];
  balance_summary: BalanceSummary;
  recommendations: string[];
}

interface StatementUploadResult {
  uploaded: boolean;
  parsed?: boolean;
  count: number;
  message?: string;
  transactions: Array<{ id?: string; party?: string; amount?: number; type?: string; date?: string; category?: string }>;
}

interface InvoiceUploadResult {
  uploaded: boolean;
  invoice?: {
    invoice_id?: string;
    party?: string;
    amount?: number;
    date?: string;
    extracted?: Record<string, any>;
  };
  linked_transaction?: {
    id?: string;
    category?: string;
    sub_category?: string;
    confidence?: number;
  } | null;
}

export default function BookkeepingPage() {
  const statementInputRef = useRef<HTMLInputElement>(null);
  const invoiceInputRef = useRef<HTMLInputElement>(null);

  const [isStatementUploading, setIsStatementUploading] = useState(false);
  const [isInvoiceUploading, setIsInvoiceUploading] = useState(false);
  const [statementUploads, setStatementUploads] = useState<string[]>([]);
  const [invoiceUploads, setInvoiceUploads] = useState<string[]>([]);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [statusType, setStatusType] = useState<'success' | 'error' | null>(null);
  const [summary, setSummary] = useState<BookkeepingSummary | null>(null);
  const [isSummaryLoading, setIsSummaryLoading] = useState(true);
  const [latestStatementResult, setLatestStatementResult] = useState<StatementUploadResult | null>(null);
  const [latestInvoiceResult, setLatestInvoiceResult] = useState<InvoiceUploadResult | null>(null);

  const userId = 'default';

  const setStatus = (message: string, type: 'success' | 'error') => {
    setStatusMessage(message);
    setStatusType(type);
  };

  const getErrorMessage = (error: unknown, fallback: string) => {
    const maybeAxios = error as {
      response?: {
        data?: {
          detail?: string;
        };
      };
      message?: string;
    };
    return maybeAxios?.response?.data?.detail || maybeAxios?.message || fallback;
  };

  const loadLedgerSummary = async () => {
    try {
      setIsSummaryLoading(true);
      const response = await apiClient.getBookkeepingLedger(userId);
      const data = response?.data;
      if (data && typeof data === 'object') {
        setSummary(data as BookkeepingSummary);
      }
    } catch (error) {
      setStatus(getErrorMessage(error, 'Unable to load bookkeeping summary'), 'error');
    } finally {
      setIsSummaryLoading(false);
    }
  };

  useEffect(() => {
    loadLedgerSummary();
  }, []);

  const triggerStatementPicker = () => {
    statementInputRef.current?.click();
  };

  const triggerInvoicePicker = () => {
    invoiceInputRef.current?.click();
  };

  const handleStatementFileChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      setIsStatementUploading(true);
      const response = await apiClient.uploadBookkeepingStatement(file, userId);
      const parsed = response?.data as StatementUploadResult | undefined;
      if (parsed) {
        setLatestStatementResult(parsed);
      }
      setStatementUploads((prev) => [file.name, ...prev]);
      await loadLedgerSummary();
      const count = parsed?.count ?? 0;
      if (count > 0) {
        setStatus(`Statement uploaded: ${file.name} • ${count} transactions parsed`, 'success');
      } else {
        setStatus(parsed?.message || 'Statement uploaded, but no transactions were parsed.', 'error');
      }
    } catch (error) {
      const message = getErrorMessage(error, 'Statement upload failed');
      setStatus(message, 'error');
    } finally {
      setIsStatementUploading(false);
      event.target.value = '';
    }
  };

  const handleInvoiceFileChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      setIsInvoiceUploading(true);
      const response = await apiClient.uploadBookkeepingInvoice(file, userId);
      const parsed = response?.data as InvoiceUploadResult | undefined;
      if (parsed) {
        setLatestInvoiceResult(parsed);
      }
      setInvoiceUploads((prev) => [file.name, ...prev]);
      await loadLedgerSummary();
      setStatus(`Invoice uploaded: ${file.name} and parsed successfully`, 'success');
    } catch (error) {
      const message = getErrorMessage(error, 'Invoice upload failed');
      setStatus(message, 'error');
    } finally {
      setIsInvoiceUploading(false);
      event.target.value = '';
    }
  };

  return (
    <PageShell
      title="Bookkeeping"
      subtitle="Manage transactions, statements, and invoices"
      headerAction={
        <div style={{ display: 'flex', gap: '1rem' }}>
          <Button
            variant="primary"
            onClick={triggerStatementPicker}
            disabled={isStatementUploading}
          >
            {isStatementUploading ? 'Uploading Statement...' : '📤 Upload Statement'}
          </Button>
          <Button
            variant="secondary"
            onClick={triggerInvoicePicker}
            disabled={isInvoiceUploading}
          >
            {isInvoiceUploading ? 'Uploading Invoice...' : '📄 Upload Invoice'}
          </Button>
        </div>
      }
    >
      <input
        ref={statementInputRef}
        type="file"
        accept=".pdf,.csv,.xlsx,.xls"
        onChange={handleStatementFileChange}
        style={{ display: 'none' }}
      />
      <input
        ref={invoiceInputRef}
        type="file"
        accept=".pdf,.png,.jpg,.jpeg"
        onChange={handleInvoiceFileChange}
        style={{ display: 'none' }}
      />

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

      <div style={{ marginBottom: '1rem' }}>
        <Card title="Transaction Summary" subtitle="Auto-generated from parsed statements and invoices">
          {isSummaryLoading ? (
            <p style={{ margin: 0, color: 'var(--muted)' }}>Loading summary...</p>
          ) : !summary?.balance_summary ? (
            <p style={{ margin: 0, color: 'var(--muted)' }}>Upload a statement or invoice to generate summary.</p>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '0.75rem' }}>
              <div style={{ background: 'var(--bg3)', borderRadius: '0.5rem', padding: '0.75rem' }}>
                <div style={{ color: 'var(--muted)', fontSize: '0.85rem' }}>Credits</div>
                <div style={{ fontWeight: 700 }}>₹{summary.balance_summary.total_credits.toFixed(2)}</div>
              </div>
              <div style={{ background: 'var(--bg3)', borderRadius: '0.5rem', padding: '0.75rem' }}>
                <div style={{ color: 'var(--muted)', fontSize: '0.85rem' }}>Debits</div>
                <div style={{ fontWeight: 700 }}>₹{summary.balance_summary.total_debits.toFixed(2)}</div>
              </div>
              <div style={{ background: 'var(--bg3)', borderRadius: '0.5rem', padding: '0.75rem' }}>
                <div style={{ color: 'var(--muted)', fontSize: '0.85rem' }}>Net Cash Flow</div>
                <div style={{ fontWeight: 700 }}>₹{summary.balance_summary.net_cash_flow.toFixed(2)}</div>
              </div>
              <div style={{ background: 'var(--bg3)', borderRadius: '0.5rem', padding: '0.75rem' }}>
                <div style={{ color: 'var(--muted)', fontSize: '0.85rem' }}>GST Paid</div>
                <div style={{ fontWeight: 700 }}>₹{summary.balance_summary.total_gst_paid.toFixed(2)}</div>
              </div>
              <div style={{ background: 'var(--bg3)', borderRadius: '0.5rem', padding: '0.75rem' }}>
                <div style={{ color: 'var(--muted)', fontSize: '0.85rem' }}>ITC Claimable</div>
                <div style={{ fontWeight: 700 }}>₹{summary.balance_summary.total_itc_claimable.toFixed(2)}</div>
              </div>
              <div style={{ background: 'var(--bg3)', borderRadius: '0.5rem', padding: '0.75rem' }}>
                <div style={{ color: 'var(--muted)', fontSize: '0.85rem' }}>Transactions</div>
                <div style={{ fontWeight: 700 }}>{summary.balance_summary.transaction_count}</div>
              </div>
            </div>
          )}
        </Card>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
        <Card title="Recent Statements" subtitle="Bank statements and records">
          <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--muted)' }}>
            {statementUploads.length === 0 ? (
              <p>No statements uploaded yet</p>
            ) : (
              <div style={{ textAlign: 'left' }}>
                {statementUploads.map((name) => (
                  <p key={name} style={{ margin: '0.25rem 0', color: 'var(--text)' }}>• {name}</p>
                ))}
              </div>
            )}
            <Button
              variant="primary"
              style={{ marginTop: '1rem' }}
              onClick={triggerStatementPicker}
              disabled={isStatementUploading}
            >
              {isStatementUploading ? 'Uploading...' : 'Upload First Statement'}
            </Button>
          </div>
        </Card>

        <Card title="Invoices" subtitle="Uploaded invoices and documents">
          <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--muted)' }}>
            {invoiceUploads.length === 0 ? (
              <p>No invoices uploaded yet</p>
            ) : (
              <div style={{ textAlign: 'left' }}>
                {invoiceUploads.map((name) => (
                  <p key={name} style={{ margin: '0.25rem 0', color: 'var(--text)' }}>• {name}</p>
                ))}
              </div>
            )}
            <Button
              variant="primary"
              style={{ marginTop: '1rem' }}
              onClick={triggerInvoicePicker}
              disabled={isInvoiceUploading}
            >
              {isInvoiceUploading ? 'Uploading...' : 'Upload First Invoice'}
            </Button>
          </div>
        </Card>

        <Card title="Latest Parsed Invoice" subtitle="Extracted data from invoice pipeline">
          <div style={{ padding: '1rem', color: 'var(--muted)' }}>
            {!latestInvoiceResult?.invoice ? (
              <p style={{ margin: 0 }}>No invoice parsed yet</p>
            ) : (
              <div style={{ display: 'grid', gap: '0.35rem' }}>
                <p style={{ margin: 0 }}><strong style={{ color: 'var(--text)' }}>Invoice ID:</strong> {latestInvoiceResult.invoice.invoice_id || '-'}</p>
                <p style={{ margin: 0 }}><strong style={{ color: 'var(--text)' }}>Party:</strong> {latestInvoiceResult.invoice.party || '-'}</p>
                <p style={{ margin: 0 }}><strong style={{ color: 'var(--text)' }}>Amount:</strong> ₹{Number(latestInvoiceResult.invoice.amount || 0).toFixed(2)}</p>
                <p style={{ margin: 0 }}><strong style={{ color: 'var(--text)' }}>Date:</strong> {latestInvoiceResult.invoice.date ? new Date(latestInvoiceResult.invoice.date).toLocaleDateString() : '-'}</p>
                {latestInvoiceResult.linked_transaction && (
                  <p style={{ margin: 0 }}>
                    <strong style={{ color: 'var(--text)' }}>Linked Category:</strong>{' '}
                    {latestInvoiceResult.linked_transaction.category || 'Uncategorized'}
                    {latestInvoiceResult.linked_transaction.sub_category ? ` / ${latestInvoiceResult.linked_transaction.sub_category}` : ''}
                  </p>
                )}
              </div>
            )}
          </div>
        </Card>

        <Card title="Sync Status" subtitle="Automatic bookkeeping updates" style={{ gridColumn: '1 / -1' }}>
          <div style={{
            padding: '1.5rem',
            background: 'var(--card-glow-emerald)',
            borderRadius: '0.5rem',
            borderLeft: '3px solid var(--emerald)',
          }}>
            <p style={{ margin: 0, color: 'var(--text)' }}>
              ✓ All systems synced. Your bookkeeping is up to date.
            </p>
            {latestStatementResult && (
              <p style={{ margin: '0.5rem 0 0 0', color: 'var(--text)' }}>
                Last statement parse: {latestStatementResult.count} transaction(s) extracted.
              </p>
            )}
            {!!summary?.recommendations?.length && (
              <div style={{ marginTop: '0.75rem' }}>
                <p style={{ margin: 0, fontWeight: 600, color: 'var(--text)' }}>Recommendations</p>
                <ul style={{ margin: '0.35rem 0 0 1.1rem', padding: 0, color: 'var(--text)' }}>
                  {summary.recommendations.slice(0, 3).map((item, idx) => (
                    <li key={idx} style={{ marginBottom: '0.2rem' }}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
            {!!summary?.balance_summary?.insights?.length && (
              <div style={{ marginTop: '0.75rem' }}>
                <p style={{ margin: 0, fontWeight: 600, color: 'var(--text)' }}>Insights</p>
                <ul style={{ margin: '0.35rem 0 0 1.1rem', padding: 0, color: 'var(--text)' }}>
                  {summary.balance_summary.insights.slice(0, 3).map((item, idx) => (
                    <li key={idx} style={{ marginBottom: '0.2rem' }}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </Card>
      </div>
    </PageShell>
  );
}
