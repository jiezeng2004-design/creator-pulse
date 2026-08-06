export type Platform = "x" | "xiaohongshu" | "zhihu" | "toutiao";

export interface Page<T> {
  page: number;
  page_size: number;
  total: number;
  items: T[];
}

export interface NextAction {
  action: string;
  label: string;
  description: string;
  requires_user_login: boolean;
}

export interface Account {
  id: number;
  platform: string;
  display_name: string;
  platform_user_id: string | null;
  username: string | null;
  avatar_url: string | null;
  account_status: string;
  authentication_type: string;
  browser_profile_path: string | null;
  last_successful_sync_at: string | null;
  last_sync_attempt_at: string | null;
  last_sync_error: string | null;
  is_mock: boolean;
  created_at: string;
  updated_at: string;
  next_action?: NextAction | null;
}

export interface Post {
  id: number;
  account_id: number;
  platform: string | null;
  account_display_name: string | null;
  platform_post_id: string;
  title: string | null;
  content_preview: string | null;
  post_url: string | null;
  post_type: string | null;
  published_at: string | null;
  metrics_updated_at: string | null;
  view_count: number | null;
  impression_count: number | null;
  like_count: number | null;
  favorite_count: number | null;
  share_count: number | null;
  repost_count: number | null;
  comment_count: number | null;
  created_at: string;
  updated_at: string;
}

export interface MetricSnapshot {
  id: number;
  post_id: number;
  captured_at: string;
  view_count: number | null;
  impression_count: number | null;
  like_count: number | null;
  favorite_count: number | null;
  share_count: number | null;
  repost_count: number | null;
  comment_count: number | null;
}

export interface Comment {
  id: number;
  post_id: number;
  account_id: number;
  platform: string | null;
  platform_comment_id: string;
  parent_comment_id: string | null;
  author_name: string | null;
  content: string;
  comment_url: string | null;
  published_at: string | null;
  like_count: number | null;
  local_status: string;
  replied_by_owner: boolean | null;
  first_seen_at: string;
  last_seen_at: string;
  post_title: string | null;
  post_url: string | null;
  account_display_name: string | null;
}

export interface PlatformCard {
  platform: string;
  platform_label: string;
  account_count: number;
  posts_last_7d: number | null;
  total_views_or_impressions: number | null;
  new_comments: number | null;
  pending_comments: number | null;
  last_sync_at: string | null;
  metric_primary_label: string;
  metric_primary_value: number | null;
  metric_secondary_label: string;
  metric_secondary_value: number | null;
  metric_tertiary_label: string;
  metric_tertiary_value: number | null;
  metric_note: string | null;
  status_summary: string;
  experimental: boolean;
  is_mock: boolean;
}

export interface DashboardSummary {
  posts_last_24h: number;
  posts_last_7d: number;
  total_views_or_impressions: number | null;
  total_engagement: number | null;
  new_comments: number;
  pending_comments: number;
  platforms: PlatformCard[];
  mock_mode: boolean;
  last_global_sync_at: string | null;
}

export interface SyncRun {
  id: number;
  account_id: number;
  platform: string;
  account_display_name: string | null;
  sync_type: string;
  status: string;
  phase: string | null;
  started_at: string;
  finished_at: string | null;
  posts_fetched: number;
  comments_fetched: number;
  error_code: string | null;
  error_message: string | null;
  diagnostic: Record<string, unknown> | null;
}

export interface Settings {
  enable_scheduled_sync: boolean;
  sync_interval_minutes: number;
  sync_max_posts: number;
  data_retention_days: number;
  dev_mode: boolean;
  enable_mock_data: boolean;
  data_dir_display: string | null;
  browser_profiles_dir_display: string | null;
  host: string;
  updated_at: string | null;
}

export interface PlatformCapability {
  platform: string;
  label: string;
  login_method: string;
  posts: string;
  views: string;
  likes: string;
  favorites: string;
  shares: string;
  comments: string;
  official_replied: string;
  local_status: string;
  stability: string;
  notes: string;
  experimental: boolean;
}
