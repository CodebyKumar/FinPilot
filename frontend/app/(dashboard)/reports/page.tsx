'use client';

import { useEffect, useMemo, useRef, useState, type ChangeEvent } from 'react';
import { PageShell } from '@/components/layout/page-shell';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { apiClient } from '@/lib/api-client';

const REPORT_TYPES = ['ITR2', 'ITR3', 'ITR4', 'GSTR1', 'GSTR3B'] as const;

type ReportType = (typeof REPORT_TYPES)[number];

interface ReportFieldItem {
  field_id?: string;
  field_name?: string;
  value?: any;
  status?: string;
  prompt?: string;
  source?: string;
}

interface ReportAnalysisResult {
  errors: Array<{ field_id?: string; message: string }>;
  warnings: Array<{ field_id?: string; message: string }>;
  suggestions: string[];
}

interface ReportState {
  reportId: string | null;
  reportName: string;
  fields: ReportFieldItem[];
  filledEntities: ReportFieldItem[];
  prefillFields: ReportFieldItem[];
  missingFields: Array<{ field_id?: string; field_name?: string; prompt?: string; source?: string }>;
  requiredUserInputs: Array<{ field_id?: string; field_name?: string; prompt?: string; source?: string }>;
  analysis: ReportAnalysisResult | null;
  validation: { valid: boolean; errors: Array<{ field_id?: string; message: string }>; warnings: Array<{ field_id?: string; message: string }>; suggestions: string[] } | null;
  status: string | null;
}

const EMPTY_REPORT_STATE: ReportState = {
  reportId: null,
  reportName: '',
  fields: [],
  filledEntities: [],
  prefillFields: [],
  missingFields: [],
  requiredUserInputs: [],
  analysis: null,
  validation: null,
  status: null,
};

export default function ReportsPage() {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [selectedReportType, setSelectedReportType] = useState<ReportType>('ITR2');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isBusy, setIsBusy] = useState(false);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [summaryMessage, setSummaryMessage] = useState<string | null>(null);
  const [summaryType, setSummaryType] = useState<'success' | 'error' | 'info' | null>(null);
  const [reportState, setReportState] = useState<ReportState>(EMPTY_REPORT_STATE);

  const userId = 'default';

  const activeFieldCount = useMemo(() => reportState.fields.length, [reportState.fields.length]);

  const setMessage = (message: string, type: 'success' | 'error' | 'info') => {
    setSummaryMessage(message);
    setSummaryType(type);
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

  const updateStateFromResponse = (data: any, fallbackReportName?: string) => {
    const report = data?.report || data || {};
    const fields = Array.isArray(report.fields) ? report.fields : Array.isArray(data?.fields) ? data.fields : [];
    setReportState((prev) => ({
      reportId: report.report_id || data?.report_id || prev.reportId,
      reportName: report.report_name || data?.report_name || fallbackReportName || prev.reportName,
      fields,
      filledEntities: Array.isArray(data?.filled_entities)
        ? data.filled_entities
        : Array.isArray(report.filled_entities)
          ? report.filled_entities
          : fields,
      prefillFields: Array.isArray(data?.prefill_fields)
        ? data.prefill_fields
        : Array.isArray(report.prefill_fields)
          ? report.prefill_fields
          : prev.prefillFields,
      missingFields: Array.isArray(report.missing_fields) ? report.missing_fields : Array.isArray(data?.missing_fields) ? data.missing_fields : prev.missingFields,
      requiredUserInputs: Array.isArray(report.required_user_inputs) ? report.required_user_inputs : Array.isArray(data?.required_user_inputs) ? data.required_user_inputs : prev.requiredUserInputs,
      analysis: data?.report_analysis || prev.analysis,
      validation: data?.valid !== undefined ? {
        valid: Boolean(data.valid),
        errors: Array.isArray(data.errors) ? data.errors : [],
        warnings: Array.isArray(data.warnings) ? data.warnings : [],
        suggestions: Array.isArray(data.suggestions) ? data.suggestions : [],
      } : prev.validation,
      status: report.status || data?.status || prev.status,
    }));
  };

  const openFilePicker = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    setSelectedFile(file);
    event.target.value = '';
    if (file) {
      setMessage(`Selected file: ${file.name}`, 'info');
    }
  };

  const runWithBusyState = async (message: string, action: () => Promise<void>) => {
    try {
      setIsBusy(true);
      setMessage(message, 'info');
      await action();
    } catch (error) {
      setMessage(getErrorMessage(error, 'Report action failed'), 'error');
    } finally {
      setIsBusy(false);
    }
  };

  const extractFields = async (reportType: ReportType) => {
    setSelectedReportType(reportType);
    await runWithBusyState(`Extracting fields for ${reportType}...`, async () => {
      const payload = { user_id: userId, report_name: reportType };
      const response = selectedFile
        ? await apiClient.extractReportFieldsFile(selectedFile, userId, reportType)
        : await apiClient.extractReportFields(payload);
      updateStateFromResponse(response?.data || response, reportType);
      const fieldCount = Array.isArray(response?.data?.fields) ? response.data.fields.length : Array.isArray(response?.fields) ? response.fields.length : 0;
      setMessage(`Extracted ${fieldCount} field(s) for ${reportType}.`, 'success');
    });
  };

  const generateReport = async (reportType: ReportType) => {
    setSelectedReportType(reportType);
    await runWithBusyState(`Generating ${reportType} report...`, async () => {
      const payload = {
        user_id: userId,
        report_name: reportType,
        report_id: reportState.reportId || undefined,
      };
      const response = selectedFile
        ? await apiClient.generateReportFile(selectedFile, userId, reportType, reportState.reportId || undefined)
        : await apiClient.generateReport(payload);
      updateStateFromResponse(response?.data || response, reportType);
      setMessage(`Report generated: ${response?.data?.report_id || response?.report_id || 'new report'}`, 'success');
    });
  };

  const analyzeReport = async (reportType: ReportType) => {
    setSelectedReportType(reportType);
    await runWithBusyState(`Analyzing ${reportType} report...`, async () => {
      const payload = {
        user_id: userId,
        report_name: reportType,
        report_id: reportState.reportId || undefined,
      };
      const response = selectedFile
        ? await apiClient.analyzeReportFile(selectedFile, userId, reportState.reportId || undefined)
        : await apiClient.analyzeReport(payload);
      updateStateFromResponse(response?.data || response, reportType);
      const analysis = response?.data?.report_analysis || response?.report_analysis;
      setReportState((prev) => ({ ...prev, analysis: analysis || prev.analysis }));
      setMessage(`Analysis completed for ${reportType}.`, 'success');
    });
  };

  const validateReport = async (reportType: ReportType) => {
    setSelectedReportType(reportType);
    await runWithBusyState(`Validating ${reportType} report...`, async () => {
      const response = await apiClient.validateReport({
        user_id: userId,
        report_name: reportType,
        report_id: reportState.reportId || undefined,
        fields: reportState.fields,
      });
      updateStateFromResponse(response?.data || response, reportType);
      const valid = Boolean(response?.data?.valid ?? response?.valid);
      setMessage(valid ? `${reportType} report is valid.` : `${reportType} report has validation issues.`, valid ? 'success' : 'error');
    });
  };

  const refreshStatus = async () => {
    if (!reportState.reportId) {
      setMessage('Generate a report first to fetch its status.', 'info');
      return;
    }

    await runWithBusyState(`Loading status for ${reportState.reportId}...`, async () => {
      const response = await apiClient.getReportStatus(reportState.reportId as string, userId);
      const data = response?.data || response;
      updateStateFromResponse(data?.report || data, selectedReportType);
      setMessage(`Status loaded for report ${reportState.reportId}.`, 'success');
    });
  };

  const runGenerateNewReport = async () => {
    await generateReport(selectedReportType);
  };

  const hydrateReportPreview = async () => {
    if (!reportState.reportId) {
      setMessage('Generate a report first, then use View Report.', 'info');
      return false;
    }

    if (reportState.fields.length === 0 || reportState.filledEntities.length === 0) {
      const response = await apiClient.getReportView(reportState.reportId, userId);
      const data = response?.data || response;
      updateStateFromResponse(data?.report || data, selectedReportType);
    }

    return true;
  };

  const openReportPreview = async () => {
    const ready = await hydrateReportPreview();
    if (!ready) return;

    setIsPreviewOpen(true);
    setMessage(`Opened report preview for ${reportState.reportId}.`, 'success');
  };

  const activeValidation = reportState.validation;
  const canViewReport = Boolean(reportState.reportId);
  const previewFields = reportState.filledEntities.length > 0
    ? reportState.filledEntities
    : reportState.fields.length > 0
      ? reportState.fields
      : reportState.prefillFields;

  const loadPrefillData = async () => {
    try {
      const response = await apiClient.getReportPrefill(userId);
      const data = response?.data || response;
      const prefillFields = Array.isArray(data?.prefill_fields) ? data.prefill_fields : [];
      setReportState((prev) => ({ ...prev, prefillFields }));
      if (prefillFields.length > 0) {
        setMessage(`Loaded ${prefillFields.length} form field(s) from profile data.`, 'success');
      }
    } catch (error) {
      setMessage(getErrorMessage(error, 'Unable to load profile data for report prefill'), 'error');
    }
  };

  useEffect(() => {
    void loadPrefillData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <PageShell
      title="Reports"
      subtitle="Generate, analyze, and submit tax reports"
      headerAction={
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          <Button variant="secondary" onClick={openFilePicker} disabled={isBusy}>
            {selectedFile ? `📎 ${selectedFile.name}` : 'Attach File'}
          </Button>
          <Button variant="primary" onClick={runGenerateNewReport} disabled={isBusy}>
            {isBusy ? 'Working...' : '+ Generate New Report'}
          </Button>
        </div>
      }
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf"
        onChange={handleFileChange}
        style={{ display: 'none' }}
      />

      {summaryMessage && summaryType && (
        <div
          style={{
            marginBottom: '1rem',
            padding: '0.75rem 1rem',
            borderRadius: '0.5rem',
            border: `1px solid ${summaryType === 'success' ? 'var(--emerald)' : summaryType === 'error' ? 'var(--rose)' : 'var(--border)'}`,
            color: summaryType === 'success' ? 'var(--emerald)' : summaryType === 'error' ? 'var(--rose)' : 'var(--text)',
            background: summaryType === 'success' ? 'var(--card-glow-emerald)' : summaryType === 'error' ? 'rgba(244, 63, 94, 0.08)' : 'var(--bg2)',
          }}
        >
          {summaryMessage}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
        <Card title="Active Report" subtitle="Current pipeline control">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem' }}>
              <span style={{ color: 'var(--muted)' }}>Selected</span>
              <Badge variant="info">{selectedReportType}</Badge>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem' }}>
              <span style={{ color: 'var(--muted)' }}>Report ID</span>
              <span style={{ color: 'var(--text)', fontWeight: 600 }}>{reportState.reportId || 'Not generated yet'}</span>
            </div>
            <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
              <Button variant="primary" onClick={() => generateReport(selectedReportType)} disabled={isBusy}>
                Generate
              </Button>
              <Button variant="secondary" onClick={() => extractFields(selectedReportType)} disabled={isBusy}>
                Extract Fields
              </Button>
              <Button variant="secondary" onClick={() => analyzeReport(selectedReportType)} disabled={isBusy}>
                Analyze
              </Button>
              <Button variant="secondary" onClick={() => validateReport(selectedReportType)} disabled={isBusy}>
                Validate
              </Button>
              <Button variant="secondary" onClick={refreshStatus} disabled={isBusy || !reportState.reportId}>
                Status
              </Button>
              <Button variant="success" onClick={openReportPreview} disabled={!canViewReport || isBusy}>
                View Report
              </Button>
            </div>
          </div>
        </Card>

        <Card title="Pipeline Snapshot" subtitle="Live result summary">
          <div style={{ display: 'grid', gap: '0.5rem' }}>
            <div><strong>Fields:</strong> {activeFieldCount}</div>
            <div><strong>Missing:</strong> {reportState.missingFields.length}</div>
            <div><strong>Required Inputs:</strong> {reportState.requiredUserInputs.length}</div>
            <div><strong>Status:</strong> {reportState.status || 'N/A'}</div>
          </div>
        </Card>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem' }}>
        {REPORT_TYPES.map((reportType) => (
          <Card key={reportType} title={reportType} subtitle="Tax return report">
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div style={{ padding: '1rem', background: 'var(--bg3)', borderRadius: '0.5rem', textAlign: 'center' }}>
                <p style={{ margin: 0, color: 'var(--muted)', fontSize: '0.9rem' }}>
                  {selectedReportType === reportType ? 'Active report type' : 'Ready to generate'}
                </p>
              </div>
              <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                <Button variant="primary" onClick={() => generateReport(reportType)} disabled={isBusy}>
                  Generate {reportType}
                </Button>
                <Button variant="secondary" onClick={() => extractFields(reportType)} disabled={isBusy}>
                  Extract
                </Button>
                <Button variant="secondary" onClick={() => analyzeReport(reportType)} disabled={isBusy}>
                  Analyze
                </Button>
                <Button variant="secondary" onClick={() => validateReport(reportType)} disabled={isBusy}>
                  Validate
                </Button>
                <Button
                  variant="success"
                  onClick={() => {
                    setSelectedReportType(reportType);
                    void openReportPreview();
                  }}
                  disabled={!canViewReport || isBusy}
                >
                  View Report
                </Button>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {isPreviewOpen && reportState.reportId && (
        <Card
          title="Filled Report Preview"
          subtitle={`Read-only preview for ${reportState.reportName || selectedReportType}`}
          style={{ marginTop: '1.5rem' }}
        >
          <div style={{ display: 'grid', gap: '1rem' }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'center' }}>
              <Badge variant="info">Report ID: {reportState.reportId}</Badge>
              <Badge variant={activeValidation?.valid ? 'success' : 'warning'}>
                {activeValidation?.valid ? 'Valid' : 'Needs Review'}
              </Badge>
              {reportState.status && <Badge variant="default">{reportState.status}</Badge>}
              <Button variant="secondary" onClick={() => setIsPreviewOpen(false)}>
                Close Preview
              </Button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
              <div style={{ padding: '1rem', background: 'var(--bg3)', borderRadius: '0.5rem' }}>
                <h4 style={{ margin: '0 0 0.75rem 0' }}>Filled Fields</h4>
                {previewFields.length === 0 ? (
                  <p style={{ margin: 0, color: 'var(--muted)' }}>No fields available.</p>
                ) : (
                  <div style={{ display: 'grid', gap: '0.5rem' }}>
                    {previewFields.map((field, index) => (
                      <div key={`${field.field_id || index}`} style={{ padding: '0.65rem', background: 'var(--bg2)', borderRadius: '0.5rem' }}>
                        <div style={{ fontWeight: 600 }}>{field.field_name || field.field_id || `Field ${index + 1}`}</div>
                        <div style={{ color: 'var(--muted)', marginTop: '0.25rem' }}>
                          {field.value === null || field.value === undefined || field.value === '' ? '—' : String(field.value)}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div style={{ padding: '1rem', background: 'var(--bg3)', borderRadius: '0.5rem' }}>
                <h4 style={{ margin: '0 0 0.75rem 0' }}>Missing / Required Inputs</h4>
                {reportState.requiredUserInputs.length === 0 ? (
                  <p style={{ margin: 0, color: 'var(--muted)' }}>Nothing pending.</p>
                ) : (
                  <ul style={{ margin: 0, paddingLeft: '1.25rem' }}>
                    {reportState.requiredUserInputs.map((item, index) => (
                      <li key={`${item.field_id || index}`} style={{ marginBottom: '0.45rem' }}>
                        <strong>{item.field_name || item.field_id || `Input ${index + 1}`}</strong>
                        <div style={{ color: 'var(--muted)' }}>{item.prompt || item.source || 'Required input'}</div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </div>
        </Card>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginTop: '1.5rem' }}>
        <Card title="Extracted Fields" subtitle="Fields returned by the report pipeline">
          {previewFields.length === 0 ? (
            <p style={{ margin: 0, color: 'var(--muted)' }}>No fields extracted yet.</p>
          ) : (
            <div style={{ display: 'grid', gap: '0.65rem' }}>
              {previewFields.map((field, index) => (
                <div key={`${field.field_id || field.field_name || index}`} style={{ padding: '0.75rem', background: 'var(--bg3)', borderRadius: '0.5rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem' }}>
                    <strong>{field.field_name || field.field_id || `Field ${index + 1}`}</strong>
                    <Badge variant={field.status === 'missing' ? 'warning' : 'success'}>{field.status || 'filled'}</Badge>
                  </div>
                  <div style={{ marginTop: '0.35rem', color: 'var(--muted)' }}>
                    {field.value === null || field.value === undefined || field.value === '' ? 'No value' : String(field.value)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title="Validation" subtitle="Errors and warnings from the validation pipeline">
          {activeValidation ? (
            <div style={{ display: 'grid', gap: '1rem' }}>
              <div><strong>Valid:</strong> {activeValidation.valid ? 'Yes' : 'No'}</div>
              <div>
                <strong>Errors:</strong>
                {activeValidation.errors.length === 0 ? (
                  <div style={{ color: 'var(--muted)' }}>No errors</div>
                ) : (
                  <ul style={{ margin: '0.5rem 0 0 1.25rem' }}>
                    {activeValidation.errors.map((item, index) => <li key={index}>{item.message}</li>)}
                  </ul>
                )}
              </div>
              <div>
                <strong>Warnings:</strong>
                {activeValidation.warnings.length === 0 ? (
                  <div style={{ color: 'var(--muted)' }}>No warnings</div>
                ) : (
                  <ul style={{ margin: '0.5rem 0 0 1.25rem' }}>
                    {activeValidation.warnings.map((item, index) => <li key={index}>{item.message}</li>)}
                  </ul>
                )}
              </div>
              <div>
                <strong>Suggestions:</strong>
                {activeValidation.suggestions.length === 0 ? (
                  <div style={{ color: 'var(--muted)' }}>No suggestions</div>
                ) : (
                  <ul style={{ margin: '0.5rem 0 0 1.25rem' }}>
                    {activeValidation.suggestions.map((item, index) => <li key={index}>{item}</li>)}
                  </ul>
                )}
              </div>
            </div>
          ) : (
            <p style={{ margin: 0, color: 'var(--muted)' }}>Run validation to see errors and warnings.</p>
          )}
        </Card>
      </div>
    </PageShell>
  );
}
