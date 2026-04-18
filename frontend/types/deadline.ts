export interface Deadline {
  id?: string;
  user_id: string;
  title: string;
  description?: string;
  due_date: string;
  deadline_type: 'tax_filing' | 'gst_filing' | 'payment' | 'audit' | 'compliance';
  status: 'pending' | 'submitted' | 'overdue';
  reminder_days?: number[];
  related_report_id?: string;
  created_at?: string;
  updated_at?: string;
}

export interface DeadlineReminder {
  id?: string;
  deadline_id: string;
  user_id: string;
  reminder_date: string;
  sent: boolean;
  notification_channel: 'email' | 'sms' | 'in_app';
  created_at?: string;
}
