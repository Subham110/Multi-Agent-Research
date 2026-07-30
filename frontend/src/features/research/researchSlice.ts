import { createAsyncThunk, createSlice, type PayloadAction } from '@reduxjs/toolkit'
import { logout } from '../auth/authSlice'
import { apiRequest } from '../../api/client'
import type { RootState } from '../../app/store'
import type {
  CreateResearchPayload,
  DashboardStats,
  ResearchEvent,
  ResearchJob,
} from '../../types'

interface ResearchState {
  jobs: ResearchJob[]
  selectedJob: ResearchJob | null
  events: ResearchEvent[]
  stats: DashboardStats | null
  loading: boolean
  creating: boolean
  error: string | null
}

const initialState: ResearchState = {
  jobs: [],
  selectedJob: null,
  events: [],
  stats: null,
  loading: false,
  creating: false,
  error: null,
}

const tokenFrom = (state: RootState) => state.auth.token

export const fetchJobs = createAsyncThunk<ResearchJob[], void, { state: RootState }>(
  'research/fetchJobs',
  async (_, { getState }) => apiRequest('/research', {}, tokenFrom(getState())),
)

export const fetchStats = createAsyncThunk<DashboardStats, void, { state: RootState }>(
  'research/fetchStats',
  async (_, { getState }) => apiRequest('/research/stats', {}, tokenFrom(getState())),
)

export const fetchJob = createAsyncThunk<ResearchJob, string, { state: RootState }>(
  'research/fetchJob',
  async (jobId, { getState }) => apiRequest(`/research/${jobId}`, {}, tokenFrom(getState())),
)

export const fetchEvents = createAsyncThunk<ResearchEvent[], string, { state: RootState }>(
  'research/fetchEvents',
  async (jobId, { getState }) => apiRequest(`/research/${jobId}/events`, {}, tokenFrom(getState())),
)


export const cancelResearch = createAsyncThunk<ResearchJob, string, { state: RootState }>(
  'research/cancelResearch',
  async (jobId, { getState }) =>
    apiRequest(`/research/${jobId}/cancel`, { method: 'POST' }, tokenFrom(getState())),
)

export const createResearch = createAsyncThunk<ResearchJob, CreateResearchPayload, { state: RootState }>(
  'research/createResearch',
  async (payload, { getState }) =>
    apiRequest('/research', { method: 'POST', body: JSON.stringify(payload) }, tokenFrom(getState())),
)

const researchSlice = createSlice({
  name: 'research',
  initialState,
  reducers: {
    selectJob(state, action: PayloadAction<ResearchJob | null>) {
      state.selectedJob = action.payload
      state.events = []
    },
    addLiveEvent(state, action: PayloadAction<ResearchEvent>) {
      const id = action.payload.id
      if (id && state.events.some((event) => event.id === id)) return
      if (action.payload.event_type !== 'heartbeat') state.events.push(action.payload)
      state.events.sort((a, b) => (a.sequence ?? 0) - (b.sequence ?? 0))
    },
    clearResearchError(state) {
      state.error = null
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(logout, () => initialState)
      .addCase(fetchJobs.pending, (state) => {
        state.loading = true
      })
      .addCase(fetchJobs.fulfilled, (state, action) => {
        state.loading = false
        state.jobs = action.payload
        if (state.selectedJob) {
          state.selectedJob = action.payload.find((job) => job.id === state.selectedJob?.id) ?? state.selectedJob
        }
      })
      .addCase(fetchJobs.rejected, (state, action) => {
        state.loading = false
        state.error = action.error.message ?? 'Could not load research jobs'
      })
      .addCase(fetchStats.fulfilled, (state, action) => {
        state.stats = action.payload
      })
      .addCase(fetchJob.fulfilled, (state, action) => {
        state.selectedJob = action.payload
        const index = state.jobs.findIndex((job) => job.id === action.payload.id)
        if (index >= 0) state.jobs[index] = action.payload
      })
      .addCase(fetchEvents.fulfilled, (state, action) => {
        state.events = action.payload
      })
      .addCase(cancelResearch.fulfilled, (state, action) => {
        state.selectedJob = action.payload
        const index = state.jobs.findIndex((job) => job.id === action.payload.id)
        if (index >= 0) state.jobs[index] = action.payload
      })
      .addCase(createResearch.pending, (state) => {
        state.creating = true
        state.error = null
      })
      .addCase(createResearch.fulfilled, (state, action) => {
        state.creating = false
        state.jobs.unshift(action.payload)
        state.selectedJob = action.payload
        state.events = []
      })
      .addCase(createResearch.rejected, (state, action) => {
        state.creating = false
        state.error = action.error.message ?? 'Could not start research'
      })
  },
})

export const { selectJob, addLiveEvent, clearResearchError } = researchSlice.actions
export default researchSlice.reducer
