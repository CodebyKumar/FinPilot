'use client';

import { useEffect, useMemo, useRef, useState, type ChangeEvent } from 'react';
import { PageShell } from '@/components/layout/page-shell';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { apiClient } from '@/lib/api-client';

const REPORT_TYPES = ['ITR-1'] as const;

const REPORT_TYPE_DETAILS: Record<ReportType, {
  subtitle: string;
  category: string;
  eligibility: string;
  coverage: string;
}> = {
  'ITR-1': {
    subtitle: 'Income Tax Return',
    category: 'Individual Return',
    eligibility: 'Resident salaried taxpayers',
    coverage: 'Salary/pension, one house property, and other income sources',
  },
};

type ReportType = (typeof REPORT_TYPES)[number];
type ReportInsightsTab = 'extracted' | 'required' | 'validation';

interface ReportFieldItem {
  field_id?: string;
  field_name?: string;
  value?: any;
  status?: string;
  prompt?: string;
  source?: string;
}

interface ReportRequiredInputItem {
  field_id?: string;
  field_name?: string;
  prompt?: string;
  source?: string;
  section?: string;
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
  missingFields: ReportRequiredInputItem[];
  requiredUserInputs: ReportRequiredInputItem[];
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

  const [selectedReportType, setSelectedReportType] = useState<ReportType | null>('ITR-1');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isBusy, setIsBusy] = useState(false);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [isSavingRequiredInputs, setIsSavingRequiredInputs] = useState(false);
  const [activeInsightsTab, setActiveInsightsTab] = useState<ReportInsightsTab>('extracted');
  const [requiredInputDrafts, setRequiredInputDrafts] = useState<Record<string, string>>({});
  const [summaryMessage, setSummaryMessage] = useState<string | null>(null);
  const [summaryType, setSummaryType] = useState<'success' | 'error' | 'info' | null>(null);
  const [reportState, setReportState] = useState<ReportState>(EMPTY_REPORT_STATE);

  const userId = 'default';

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

  const getSelectedReportTypeOrNotify = (): ReportType | null => {
    if (!selectedReportType) {
      setMessage('Select a report type from the report card first.', 'info');
      return null;
    }
    return selectedReportType;
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
      updateStateFromResponse(data?.report || data, selectedReportType || undefined);
      setMessage(`Status loaded for report ${reportState.reportId}.`, 'success');
    });
  };

  const runGenerateNewReport = async () => {
    const reportType = getSelectedReportTypeOrNotify();
    if (!reportType) return;
    await generateReport(reportType);
  };

  const hydrateReportPreview = async () => {
    if (!reportState.reportId) {
      setMessage('Generate a report first, then use View Report.', 'info');
      return false;
    }

    if (reportState.fields.length === 0 || reportState.filledEntities.length === 0) {
      const response = await apiClient.getReportView(reportState.reportId, userId);
      const data = response?.data || response;
      updateStateFromResponse(data?.report || data, selectedReportType || undefined);
    }

    return true;
  };

  const openReportPreview = async () => {
    const ready = await hydrateReportPreview();
    if (!ready) return;

    setIsPreviewOpen(true);
    setMessage(`Opened report preview for ${reportState.reportId}.`, 'success');
  };

  const downloadCurrentReport = async () => {
    if (!reportState.reportId) {
      setMessage('Generate a report first, then download it.', 'info');
      return;
    }

    await runWithBusyState(`Preparing download for ${reportState.reportId}...`, async () => {
      const { blob, filename } = await apiClient.downloadReport(reportState.reportId as string, userId);
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.URL.revokeObjectURL(url);
      setMessage(`Downloaded report: ${filename}`, 'success');
    });
  };

  const sendCurrentReportViaSmtp = async () => {
    if (!reportState.reportId) {
      setMessage('Generate a report first, then email it.', 'info');
      return;
    }

    await runWithBusyState(`Sending report ${reportState.reportId} via SMTP...`, async () => {
      const response = await apiClient.sendReportEmail({
        user_id: userId,
        report_id: reportState.reportId as string,
      });

      const data = response?.data || response;
      const recipient = data?.recipient || 'your registered email';
      setMessage(`Report sent to ${recipient}.`, 'success');
    });
  };

  const activeValidation = reportState.validation;
  const canViewReport = Boolean(reportState.reportId);
  const hasSelectedReportType = Boolean(selectedReportType);
  const rawPreviewFields = reportState.filledEntities.length > 0
    ? reportState.filledEntities
    : reportState.fields.length > 0
      ? reportState.fields
      : reportState.prefillFields;

  const normalizedSelectedReportType = (selectedReportType || '').replace(/[^a-zA-Z0-9]/g, '').toUpperCase();
  const normalizedActiveReportName = String(reportState.reportName || '').replace(/[^a-zA-Z0-9]/g, '').toUpperCase();
  const isSelectedReportMatching = Boolean(selectedReportType) && (
    normalizedActiveReportName === '' || normalizedActiveReportName === normalizedSelectedReportType
  );

  const previewFields = isSelectedReportMatching ? rawPreviewFields : [];
  const visibleRequiredUserInputs = isSelectedReportMatching ? reportState.requiredUserInputs : [];
  const emptyFieldMessage = !hasSelectedReportType
    ? 'Select a report type to view fields.'
    : !isSelectedReportMatching
      ? `No fields available for ${selectedReportType}.`
      : 'No fields available.';

  const buildRequiredInputKey = (item: ReportRequiredInputItem, index: number) => {
    return item.field_id || item.field_name || `required-${index}`;
  };

  const formatRequiredGroupTitle = (item: ReportRequiredInputItem) => {
    const raw = String(item.section || item.source || item.field_id?.split('.')[0] || 'General').trim();
    return raw
      .replace(/[._]+/g, ' ')
      .replace(/\s+/g, ' ')
      .trim()
      .replace(/\b\w/g, (char) => char.toUpperCase()) || 'General';
  };

  const parseSingleSelectOptions = (item: ReportRequiredInputItem): string[] => {
    const promptText = String(item.prompt || '');
    if (!promptText) return [];

    const normalizedPrompt = promptText.replace(/\r\n/g, '\n').trim();

    const numberedOptions = Array.from(
      normalizedPrompt.matchAll(/(?:^|\n)\s*(?:\d+|[A-Za-z])[).:-]\s*([^\n]+)/g),
    )
      .map((match) => String(match[1] || '').trim())
      .filter(Boolean);

    if (numberedOptions.length >= 2 && numberedOptions.length <= 6) {
      return Array.from(new Set(numberedOptions));
    }

    const optionText = normalizedPrompt.match(/(?:select|choose|options?|answer)\s*[:\-]\s*(.+)$/i)?.[1] || normalizedPrompt;
    const splitOptions = optionText
      .split(/\s*(?:\/|\||,)\s*/)
      .map((value) => value.trim())
      .filter((value) => value.length > 0 && value.length <= 45);

    if (splitOptions.length >= 2 && splitOptions.length <= 6) {
      return Array.from(new Set(splitOptions));
    }

    return [];
  };

  const shouldSpanRequiredInputCard = (item: ReportRequiredInputItem) => {
    const promptText = String(item.prompt || '');
    const fieldText = String(item.field_name || item.field_id || '');
    const combinedLength = `${fieldText} ${promptText}`.trim().length;
    return combinedLength > 120 || promptText.includes('\n');
  };

  const requiredInputGroups = useMemo(() => {
    const groups: Array<{
      title: string;
      items: Array<{ item: ReportRequiredInputItem; originalIndex: number }>;
    }> = [];
    const groupIndexMap = new Map<string, number>();

    visibleRequiredUserInputs.forEach((item, index) => {
      const title = formatRequiredGroupTitle(item);
      const foundIndex = groupIndexMap.get(title);

      if (foundIndex === undefined) {
        groupIndexMap.set(title, groups.length);
        groups.push({ title, items: [{ item, originalIndex: index }] });
      } else {
        groups[foundIndex].items.push({ item, originalIndex: index });
      }
    });

    return groups;
  }, [visibleRequiredUserInputs]);

  const inferInputType = (label: string) => {
    const text = label.toLowerCase();
    if (text.includes('email')) return 'email';
    if (text.includes('date') || text.includes('dob')) return 'date';
    if (text.includes('mobile') || text.includes('phone') || text.includes('contact')) return 'tel';
    return 'text';
  };

  const getExistingFieldValue = (fieldId?: string, fieldName?: string) => {
    if (fieldId) {
      const byId = reportState.fields.find((field) => field.field_id === fieldId);
      if (byId && byId.value !== undefined && byId.value !== null) {
        return String(byId.value);
      }
    }

    if (fieldName) {
      const byName = reportState.fields.find((field) => field.field_name === fieldName);
      if (byName && byName.value !== undefined && byName.value !== null) {
        return String(byName.value);
      }
    }

    return '';
  };

  const loadPrefillData = async () => {
    try {
      const response = await apiClient.getReportPrefill(userId);
      const data = response?.data || response;
      updateStateFromResponse(data, selectedReportType || undefined);
      const prefillFields = Array.isArray(data?.prefill_fields) ? data.prefill_fields : Array.isArray(data?.fields) ? data.fields : [];
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

  useEffect(() => {
    setRequiredInputDrafts((prev) => {
      const next = { ...prev };
      const activeKeys = new Set<string>();

      visibleRequiredUserInputs.forEach((item, index) => {
        const key = buildRequiredInputKey(item, index);
        activeKeys.add(key);
        if (next[key] === undefined) {
          next[key] = getExistingFieldValue(item.field_id, item.field_name);
        }
      });

      Object.keys(next).forEach((key) => {
        if (!activeKeys.has(key)) {
          delete next[key];
        }
      });

      return next;
    });
  }, [visibleRequiredUserInputs, reportState.fields]);

  useEffect(() => {
    if (activeInsightsTab === 'required' && reportState.requiredUserInputs.length === 0) {
      setActiveInsightsTab('extracted');
    }
  }, [activeInsightsTab, reportState.requiredUserInputs.length]);

  const handleDraftChange = (key: string, value: string) => {
    setRequiredInputDrafts((prev) => ({ ...prev, [key]: value }));
  };

  const saveRequiredInputs = async () => {
    if (visibleRequiredUserInputs.length === 0) {
      setMessage('No pending required inputs to save.', 'info');
      return;
    }

    try {
      setIsSavingRequiredInputs(true);
      const nextFields: ReportFieldItem[] = reportState.fields.map((field) => ({ ...field }));

      visibleRequiredUserInputs.forEach((item, index) => {
        const key = buildRequiredInputKey(item, index);
        const value = (requiredInputDrafts[key] ?? '').trim();
        if (!value) return;

        const byIdIndex = item.field_id
          ? nextFields.findIndex((field) => field.field_id === item.field_id)
          : -1;

        if (byIdIndex >= 0) {
          nextFields[byIdIndex] = {
            ...nextFields[byIdIndex],
            value,
            status: 'filled',
            source: 'manual_user_input',
          };
          return;
        }

        const byNameIndex = item.field_name
          ? nextFields.findIndex((field) => field.field_name === item.field_name)
          : -1;

        if (byNameIndex >= 0) {
          nextFields[byNameIndex] = {
            ...nextFields[byNameIndex],
            value,
            status: 'filled',
            source: 'manual_user_input',
          };
          return;
        }

        nextFields.push({
          field_id: item.field_id || key,
          field_name: item.field_name || key,
          value,
          status: 'filled',
          source: 'manual_user_input',
          prompt: item.prompt,
        });
      });

      const response = await apiClient.generateReport({
        user_id: userId,
        report_name: selectedReportType,
        report_id: reportState.reportId || undefined,
        fields: nextFields,
        sync_profile: true,
      });

      updateStateFromResponse(response?.data || response, selectedReportType || undefined);
      setMessage('Saved required inputs and synced report/profile successfully.', 'success');
    } catch (error) {
      setMessage(getErrorMessage(error, 'Failed to save required inputs'), 'error');
    } finally {
      setIsSavingRequiredInputs(false);
    }
  };

  return (
    <PageShell
      title="Reports"
      subtitle="Generate, analyze, and submit tax reports"
      headerAction={
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          <Button variant="secondary" onClick={openFilePicker} disabled={isBusy}>
            {selectedFile ? `📎 ${selectedFile.name}` : 'Attach File'}
          </Button>
          <Button variant="primary" onClick={runGenerateNewReport} disabled={isBusy || !hasSelectedReportType}>
            {isBusy ? 'Working...' : hasSelectedReportType ? '+ Generate New Report' : 'Select Report Type'}
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

      <div
        style={{
          display: 'grid',
          gap: '1.5rem',
        }}
      >
        <div style={{ minWidth: 0 }}>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
        <Card title="Active Report" subtitle="Current pipeline control">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem' }}>
              <span style={{ color: 'var(--muted)' }}>Selected</span>
              <Badge variant={hasSelectedReportType ? 'info' : 'warning'}>{selectedReportType || 'None'}</Badge>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem' }}>
              <span style={{ color: 'var(--muted)' }}>Report ID</span>
              <span style={{ color: 'var(--text)', fontWeight: 600 }}>{reportState.reportId || 'Not generated yet'}</span>
            </div>
            <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
              <Button
                variant="primary"
                onClick={() => {
                  const reportType = getSelectedReportTypeOrNotify();
                  if (!reportType) return;
                  void generateReport(reportType);
                }}
                disabled={isBusy || !hasSelectedReportType}
              >
                Generate
              </Button>
              <Button
                variant="secondary"
                onClick={() => {
                  const reportType = getSelectedReportTypeOrNotify();
                  if (!reportType) return;
                  void validateReport(reportType);
                }}
                disabled={isBusy || !hasSelectedReportType}
              >
                Validate
              </Button>
              <Button variant="secondary" onClick={refreshStatus} disabled={isBusy || !reportState.reportId}>
                Status
              </Button>
              <Button variant="success" onClick={openReportPreview} disabled={!canViewReport || isBusy}>
                View Report
              </Button>
              <Button variant="secondary" onClick={downloadCurrentReport} disabled={!canViewReport || isBusy}>
                Download Report
              </Button>
              <Button variant="secondary" onClick={sendCurrentReportViaSmtp} disabled={!canViewReport || isBusy}>
                Send via SMTP
              </Button>
            </div>
          </div>
        </Card>

      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem' }}>
        {REPORT_TYPES.map((reportType) => (
          <Card key={reportType} title={reportType} subtitle={REPORT_TYPE_DETAILS[reportType].subtitle}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div
                style={{
                  padding: '1rem',
                  background: selectedReportType === reportType
                    ? 'linear-gradient(135deg, rgba(16, 185, 129, 0.16) 0%, rgba(16, 185, 129, 0.04) 100%)'
                    : 'var(--bg3)',
                  borderRadius: '0.5rem',
                  border: selectedReportType === reportType
                    ? '1px solid rgba(16, 185, 129, 0.45)'
                    : '1px solid var(--border)',
                  boxShadow: selectedReportType === reportType
                    ? '0 8px 20px rgba(16, 185, 129, 0.12)'
                    : 'none',
                  display: 'grid',
                  gap: '0.55rem',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem' }}>
                  <strong style={{ fontSize: '0.95rem' }}>Return Profile</strong>
                  <Badge variant={selectedReportType === reportType ? 'success' : 'info'}>
                    {selectedReportType === reportType ? 'Selected' : 'Available'}
                  </Badge>
                </div>
                <div style={{ color: 'var(--muted)', fontSize: '0.88rem' }}>
                  <strong>Category:</strong> {REPORT_TYPE_DETAILS[reportType].category}
                </div>
                <div style={{ color: 'var(--muted)', fontSize: '0.88rem' }}>
                  <strong>Eligibility:</strong> {REPORT_TYPE_DETAILS[reportType].eligibility}
                </div>
                <div style={{ color: 'var(--muted)', fontSize: '0.86rem' }}>
                  <strong>Coverage:</strong> {REPORT_TYPE_DETAILS[reportType].coverage}
                </div>
              </div>
              <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                {selectedReportType === reportType ? (
                  <>
                    <Button variant="secondary" disabled>
                      {reportType} Selected
                    </Button>
                    <Button
                      variant="secondary"
                      onClick={() => {
                        setSelectedReportType(null);
                        setMessage(`${reportType} unselected. Select a report type to continue.`, 'info');
                      }}
                      disabled={isBusy}
                    >
                      Unselect
                    </Button>
                  </>
                ) : (
                  <Button
                    variant="primary"
                    onClick={() => {
                      setSelectedReportType(reportType);
                      setMessage(`${reportType} selected. Use Active Report controls above.`, 'success');
                    }}
                    disabled={isBusy}
                  >
                    Select {reportType}
                  </Button>
                )}
              </div>
            </div>
          </Card>
        ))}
      </div>

      {isPreviewOpen && reportState.reportId && (
        <Card
          title="Filled Report Preview"
          subtitle={`Read-only preview for ${reportState.reportName || selectedReportType || 'Report'}`}
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
                  <p style={{ margin: 0, color: 'var(--muted)' }}>{emptyFieldMessage}</p>
                ) : (
                  <div style={{ display: 'grid', gap: '0.5rem' }}>
                    {previewFields.map((field, index) => (
                      <div key={`${field.field_id || index}`} style={{ padding: '0.65rem', background: 'var(--bg2)', borderRadius: '0.5rem' }}>
                        <div style={{ fontWeight: 600 }}>{field.field_name || field.field_id || `Field ${index + 1}`}</div>
                        <div style={{ marginTop: '0.2rem', color: 'var(--muted)', fontSize: '0.82rem' }}>
                          Identifier: {field.field_id || `Field-${index + 1}`}
                        </div>
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
                {visibleRequiredUserInputs.length === 0 ? (
                  <p style={{ margin: 0, color: 'var(--muted)' }}>Nothing pending.</p>
                ) : (
                  <ul style={{ margin: 0, paddingLeft: '1.25rem' }}>
                    {visibleRequiredUserInputs.map((item, index) => (
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

      <Card
        title="Report Insights"
        subtitle="Switch between Extracted Fields, Required Fields, and Validation"
        style={{ marginTop: '1.5rem' }}
      >
        <div style={{ display: 'grid', gap: '1rem' }}>
          <div
            role="tablist"
            aria-label="Report insights tabs"
            style={{ display: 'flex', flexWrap: 'wrap', gap: '0.65rem' }}
          >
            <Button
              variant={activeInsightsTab === 'extracted' ? 'primary' : 'secondary'}
              onClick={() => setActiveInsightsTab('extracted')}
            >
              Extracted Fields ({previewFields.length})
            </Button>
            <Button
              variant={activeInsightsTab === 'required' ? 'primary' : 'secondary'}
              onClick={() => setActiveInsightsTab('required')}
            >
              Required Fields ({visibleRequiredUserInputs.length})
            </Button>
            <Button
              variant={activeInsightsTab === 'validation' ? 'primary' : 'secondary'}
              onClick={() => setActiveInsightsTab('validation')}
            >
              Validation
            </Button>
          </div>

          {activeInsightsTab === 'extracted' && (
            <div role="tabpanel" aria-label="Extracted fields panel">
              {previewFields.length === 0 ? (
                <p style={{ margin: 0, color: 'var(--muted)' }}>No fields extracted yet.</p>
              ) : (
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
                    gap: '0.75rem',
                  }}
                >
                  {previewFields.map((field, index) => (
                    <div
                      key={`${field.field_id || field.field_name || index}`}
                      style={{
                        padding: '0.85rem',
                        background: 'var(--bg3)',
                        borderRadius: '0.5rem',
                        border: '1px solid var(--border)',
                        minHeight: '88px',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem' }}>
                        <strong>{field.field_name || field.field_id || `Field ${index + 1}`}</strong>
                        <Badge variant={field.status === 'missing' ? 'warning' : 'success'}>{field.status || 'filled'}</Badge>
                      </div>
                      <div style={{ marginTop: '0.2rem', color: 'var(--muted)', fontSize: '0.82rem' }}>
                        Identifier: {field.field_id || `Field-${index + 1}`}
                      </div>
                      <div style={{ marginTop: '0.35rem', color: 'var(--muted)' }}>
                        {field.value === null || field.value === undefined || field.value === '' ? 'No value' : String(field.value)}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeInsightsTab === 'required' && (
            <div role="tabpanel" aria-label="Required fields panel">
              {visibleRequiredUserInputs.length === 0 ? (
                <p style={{ margin: 0, color: 'var(--muted)' }}>No required fields pending right now.</p>
              ) : (
                <div style={{ display: 'grid', gap: '1rem' }}>
                  {requiredInputGroups.map((group) => (
                    <div key={group.title} style={{ display: 'grid', gap: '0.7rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
                        <Badge variant="info">{group.title}</Badge>
                        <span style={{ color: 'var(--muted)', fontSize: '0.82rem' }}>
                          {group.items.length} question(s)
                        </span>
                      </div>

                      <div
                        style={{
                          display: 'grid',
                          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                          gap: '0.9rem',
                        }}
                      >
                        {group.items.map(({ item, originalIndex }) => {
                          const key = buildRequiredInputKey(item, originalIndex);
                          const label = item.field_name || item.field_id || `Input ${originalIndex + 1}`;
                          const prompt = item.prompt || 'Required input';
                          const options = parseSingleSelectOptions(item);
                          const hasSingleSelectOptions = options.length >= 2;
                          const selectedValue = requiredInputDrafts[key] ?? '';

                          return (
                            <div
                              key={key}
                              style={{
                                display: 'grid',
                                gap: '0.55rem',
                                padding: '0.75rem',
                                borderRadius: '0.5rem',
                                border: '1px solid var(--border)',
                                background: 'var(--bg3)',
                                gridColumn: shouldSpanRequiredInputCard(item) ? '1 / -1' : undefined,
                              }}
                            >
                              <div style={{ display: 'grid', gap: '0.2rem' }}>
                                <strong style={{ fontSize: '0.92rem' }}>{label}</strong>
                                <p style={{ margin: 0, fontSize: '0.82rem', color: 'var(--muted)' }}>{prompt}</p>
                                <p style={{ margin: 0, fontSize: '0.78rem', color: 'var(--muted)' }}>
                                  Identifier: {item.field_id || `Field-${originalIndex + 1}`}
                                </p>
                              </div>

                              {hasSingleSelectOptions ? (
                                <div style={{ display: 'grid', gap: '0.45rem' }}>
                                  {options.map((option) => {
                                    const isChecked = selectedValue === option;
                                    return (
                                      <label
                                        key={`${key}-${option}`}
                                        style={{
                                          display: 'flex',
                                          alignItems: 'center',
                                          gap: '0.5rem',
                                          padding: '0.55rem 0.65rem',
                                          borderRadius: '0.45rem',
                                          border: isChecked ? '1px solid var(--emerald)' : '1px solid var(--border)',
                                          background: isChecked ? 'var(--card-glow-emerald)' : 'var(--bg2)',
                                          cursor: 'pointer',
                                        }}
                                      >
                                        <input
                                          type="radio"
                                          name={`required-choice-${key}`}
                                          value={option}
                                          checked={isChecked}
                                          onChange={(event) => handleDraftChange(key, event.target.value)}
                                        />
                                        <span style={{ color: 'var(--text)', fontSize: '0.88rem' }}>{option}</span>
                                      </label>
                                    );
                                  })}
                                </div>
                              ) : (
                                <Input
                                  label="Answer"
                                  type={inferInputType(label)}
                                  value={selectedValue}
                                  onChange={(event) => handleDraftChange(key, event.target.value)}
                                />
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ))}

                  <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                    <Button
                      variant="primary"
                      onClick={saveRequiredInputs}
                      disabled={isSavingRequiredInputs || isBusy}
                    >
                      {isSavingRequiredInputs ? 'Saving...' : 'Save Required Inputs'}
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}

          {activeInsightsTab === 'validation' && (
            <div role="tabpanel" aria-label="Validation panel">
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
            </div>
          )}
        </div>
      </Card>

        </div>

      </div>

    </PageShell>
  );
}
