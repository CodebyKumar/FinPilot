export type ReportType = 'ITR2' | 'ITR3' | 'ITR4' | 'GSTR1' | 'GSTR3B' | 'GST_AUDIT' | 'FINANCIAL_STATEMENT';

export interface ReportField {
  id: string;
  name: string;
  label: string;
  type: 'text' | 'number' | 'date' | 'select' | 'textarea' | 'currency';
  required: boolean;
  value?: any;
  source?: string;
  confidence?: number;
  error?: string;
  options?: Array<{ label: string; value: string }>;
}

export interface Report {
  id?: string;
  user_id: string;
  report_type: ReportType;
  status: 'draft' | 'ready' | 'submitted' | 'rejected';
  fields: ReportField[];
  validation_result?: ValidationResult;
  submission_date?: string;
  rejection_reason?: string;
  created_at?: string;
  updated_at?: string;
}

export interface ValidationResult {
  is_valid: boolean;
  errors: ValidationError[];
  warnings: ValidationWarning[];
}

export interface ValidationError {
  field_id: string;
  message: string;
  severity: 'error';
}

export interface ValidationWarning {
  field_id: string;
  message: string;
  severity: 'warning';
  suggestion?: string;
}
