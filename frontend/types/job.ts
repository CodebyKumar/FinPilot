export interface Job {
  id: string;
  user_id: string;
  task_name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress?: number;
  data?: any;
  errors?: string[];
  warnings?: string[];
  correlation_id?: string;
  created_at: string;
  updated_at: string;
  completed_at?: string;
}

export interface ExecuteRequest {
  task_name: string;
  user_id: string;
  payload: Record<string, any>;
  mode: 'sync' | 'async';
  idempotency_key?: string;
}

export interface ExecuteResponse {
  status: 'success' | 'accepted' | 'error';
  task_name: string;
  user_id: string;
  data?: any;
  errors?: string[];
  warnings?: string[];
  correlation_id: string;
  job_id?: string;
}
