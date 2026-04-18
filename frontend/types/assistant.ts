export interface ChatMessage {
  id?: string;
  user_id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  context?: ChatContext;
  citations?: string[];
}

export interface ChatContext {
  profile_id?: string;
  transaction_id?: string;
  report_id?: string;
  deadline_id?: string;
}

export interface AssistantResponse {
  message: string;
  suggestions?: string[];
  context?: ChatContext;
  actions?: AssistantAction[];
}

export interface AssistantAction {
  action_type: 'navigate' | 'update_field' | 'generate_report' | 'suggest_deadline';
  target: string;
  payload?: Record<string, any>;
}
