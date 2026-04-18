export interface Invoice {
  id?: string;
  user_id: string;
  file_name: string;
  file_path: string;
  invoice_number: string;
  invoice_date: string;
  due_date: string;
  vendor: string;
  amount: number;
  currency: string;
  items: InvoiceItem[];
  tax_amount?: number;
  total_amount: number;
  status: 'pending' | 'matched' | 'reconciled';
  parsed_data?: Record<string, any>;
  created_at?: string;
  updated_at?: string;
}

export interface InvoiceItem {
  description: string;
  quantity: number;
  unit_price: number;
  amount: number;
  tax_rate?: number;
}
