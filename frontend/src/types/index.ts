export type JobStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'
export type ResearchDepth = 'quick' | 'standard' | 'deep'

export interface User {
  id: string
  email: string
  full_name: string
  role: string
  tenant_id: string
  tenant_slug: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}

export interface ResearchSource {
  id: string
  title: string
  url: string
  source_type: string
  authors: string[]
  published_at: string | null
  abstract: string
  excerpt: string
  credibility_score: number
}

export interface ResearchReport {
  id: string
  title: string
  executive_summary: string
  markdown: string
  quality_score: number
  citation_count: number
  metadata: Record<string, unknown>
  version: number
  created_at: string
}

export interface ResearchJob {
  id: string
  topic: string
  objective: string
  depth: ResearchDepth
  status: JobStatus
  current_agent: string | null
  progress: number
  error: string | null
  created_at: string
  started_at: string | null
  completed_at: string | null
  report: ResearchReport | null
  sources: ResearchSource[]
}

export interface ResearchEvent {
  id?: string
  sequence?: number
  event_type: string
  agent?: string | null
  message?: string
  payload?: Record<string, unknown>
  created_at?: string
}

export interface DashboardStats {
  total_jobs: number
  completed_jobs: number
  running_jobs: number
  failed_jobs: number
  average_quality_score: number
  total_sources: number
}

export interface CreateResearchPayload {
  topic: string
  objective: string
  depth: ResearchDepth
  max_reflections: number
  max_revisions: number
  focus_urls: string[]
}
