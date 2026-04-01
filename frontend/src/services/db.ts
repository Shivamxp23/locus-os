import Dexie, { Table } from 'dexie';
import type { Task, Goal, OfflineQueueItem, DailyMetrics, PersonalitySnapshot } from '../types/models';

export interface TaskCache extends Task {}
export interface GoalCache extends Goal {}
export interface HabitCache {
  id: string;
  user_id: string;
  title: string;
  frequency: string;
  current_streak: number;
  is_active: boolean;
  last_completed: string | null;
}
export interface DailyMetricsCache extends DailyMetrics {}
export interface PersonalitySnapshotCache extends PersonalitySnapshot {}
export interface ScheduleBlock {
  id: string;
  user_id: string;
  task_id: string;
  start_time: string;
  end_time: string;
  block_type: string;
}
export interface RecommendationCache {
  id: string;
  user_id: string;
  rec_type: string;
  title: string;
  relevance_reason: string;
  status: string;
  created_at: string;
}
export interface InsightCache {
  id: string;
  user_id: string;
  insight_type: string;
  title: string;
  content: string;
  read_by_user: boolean;
  created_at: string;
}

class LocusDB extends Dexie {
  tasks!: Table<TaskCache>;
  goals!: Table<GoalCache>;
  habits!: Table<HabitCache>;
  daily_metrics!: Table<DailyMetricsCache>;
  personality_snapshot!: Table<PersonalitySnapshotCache>;
  offline_queue!: Table<OfflineQueueItem>;
  schedule_cache!: Table<ScheduleBlock>;
  recommendations_cache!: Table<RecommendationCache>;
  insights_cache!: Table<InsightCache>;

  constructor() {
    super('LocusDB');

    this.version(1).stores({
      tasks: '&id, user_id, status, goal_id, scheduled_at, updated_at',
      goals: '&id, user_id, is_active, horizon',
      habits: '&id, user_id, is_active, last_completed',
      daily_metrics: '&[user_id+date], user_id, date',
      personality_snapshot: '&id, user_id, generated_at',
      offline_queue: '++local_id, id, sync_status, type, created_at',
      schedule_cache: '&id, user_id, start_time, block_type',
      recommendations_cache: '&id, user_id, rec_type, status, created_at',
      insights_cache: '&id, user_id, insight_type, read_by_user, created_at'
    });
  }
}

export const db = new LocusDB();
