export interface User {
  id: string;
  email: string;
  display_name: string;
  timezone: string;
  genesis_completed: boolean;
  telegram_chat_id: string | null;
  google_refresh_token: string | null;
  is_active: boolean;
}

export interface Task {
  id: string;
  user_id: string;
  title: string;
  description: string;
  parent_task_id: string | null;
  goal_id: string | null;
  project_id: string | null;
  source: string;
  notion_page_id: string | null;
  status: string;
  priority_score: number | null;
  energy_type: string | null;
  estimated_minutes: number | null;
  scheduled_at: string | null;
  deferral_count: number;
  deferral_flag: string | null;
  completed_at: string | null;
  completion_duration_minutes: number | null;
  engine_annotations: string | null;
  created_at: string;
  updated_at: string;
  deadline: string | null;
}

export interface Goal {
  id: string;
  user_id: string;
  title: string;
  description: string;
  horizon: string;
  progress_score: number;
  neo4j_node_id: string | null;
  notion_page_id: string | null;
  is_active: boolean;
  is_stale: boolean;
  stale_since: string | null;
  created_at: string;
  updated_at: string;
  last_task_completed: string | null;
  deadline: string | null;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
}

export interface OfflineQueueItem {
  local_id?: number;
  id: string;
  created_at: number;
  type: string;
  payload: Record<string, unknown>;
  sync_status: 'pending' | 'syncing' | 'synced' | 'failed';
  retry_count: number;
  last_retry: number | null;
  device_id: string;
}

export interface DailyMetrics {
  user_id: string;
  date: string;
  tasks_completed: number;
  tasks_deferred: number;
  tasks_created: number;
  deep_work_minutes: number;
  creative_minutes: number;
  dominant_topic: string | null;
  dominant_category: string | null;
  obsidian_log_path: string | null;
}

export interface PersonalitySnapshot {
  generated_at: string;
  user_id: string;
  is_fallback: boolean;
  tasks: Task[];
  goals: Goal[];
  behavioral_summary: {
    events_today: number;
    avg_mood: number;
  };
}

export interface SyncStatus {
  last_sync: string | null;
  pending_server_items: number;
}

export interface IntegrationStatus {
  notion: { connected: boolean; last_sync: string | null };
  google_calendar: { connected: boolean; last_sync: string | null };
  telegram: { connected: boolean; chat_id: string | null };
}

export interface AiConversation {
  id: string;
  model_used: string;
  model_source: string;
  summary: string | null;
  topic_tags: string[];
  created_at: string;
}

export interface FullConversation extends AiConversation {
  messages: Array<{ role: string; content: string }>;
  token_count: number | null;
  obsidian_path: string | null;
}
