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

export type AssistantCapability = 'bookkeeping' | 'deadline' | 'report' | 'general';

export interface AssistantCapabilityResult {
  capability?: AssistantCapability | string;
  result?: Record<string, any>;
}

export interface AssistantOrchestratorResponse {
  user_id: string;
  input_query: string;
  agent_response: string;
  capability?: AssistantCapability | string;
  capability_result?: AssistantCapabilityResult | Record<string, any>;
  trace?: {
    route?: string;
    query_type?: string;
    agents_used?: string[];
    resources_used?: string[];
  };
}

export interface AssistantChatEnvelope {
  answered?: boolean;
  error?: string;
  response?: AssistantOrchestratorResponse;
}

export interface AssistantGraphMetadata {
  version?: string;
  nodes?: string[];
  routes?: string[];
}

export interface AssistantGraphEnvelope {
  format?: string;
  graph?: string;
  metadata?: AssistantGraphMetadata;
}
