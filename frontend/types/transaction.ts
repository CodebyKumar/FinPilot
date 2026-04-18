export interface Transaction {
  id?: string;
  user_id: string;
  date: string;
  amount: number;
  description: string;
  category: string;
  source: 'bank_statement' | 'invoice' | 'manual' | 'sms';
  confidence?: number;
  tags?: string[];
  metadata?: Record<string, any>;
  created_at?: string;
  updated_at?: string;
}

export interface Ledger {
  id?: string;
  user_id: string;
  transactions: Transaction[];
  total_income: number;
  total_expenses: number;
  net_profit: number;
  period_start: string;
  period_end: string;
  created_at?: string;
  updated_at?: string;
}
