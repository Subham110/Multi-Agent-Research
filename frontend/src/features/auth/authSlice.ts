import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import { apiRequest } from '../../api/client'
import type { AuthResponse, User } from '../../types'

interface AuthState {
  token: string | null
  user: User | null
  loading: boolean
  error: string | null
}

const storedToken = localStorage.getItem('researchmesh_token')
const storedUser = localStorage.getItem('researchmesh_user')

const initialState: AuthState = {
  token: storedToken,
  user: storedUser ? (JSON.parse(storedUser) as User) : null,
  loading: false,
  error: null,
}

export const login = createAsyncThunk(
  'auth/login',
  async (payload: { email: string; password: string; tenant_slug: string }) =>
    apiRequest<AuthResponse>('/auth/login', { method: 'POST', body: JSON.stringify(payload) }),
)

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    logout(state) {
      state.token = null
      state.user = null
      localStorage.removeItem('researchmesh_token')
      localStorage.removeItem('researchmesh_user')
    },
    clearAuthError(state) {
      state.error = null
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(login.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(login.fulfilled, (state, action) => {
        state.loading = false
        state.token = action.payload.access_token
        state.user = action.payload.user
        localStorage.setItem('researchmesh_token', action.payload.access_token)
        localStorage.setItem('researchmesh_user', JSON.stringify(action.payload.user))
      })
      .addCase(login.rejected, (state, action) => {
        state.loading = false
        state.error = action.error.message ?? 'Login failed'
      })
  },
})

export const { logout, clearAuthError } = authSlice.actions
export default authSlice.reducer
