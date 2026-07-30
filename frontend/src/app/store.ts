import { configureStore } from '@reduxjs/toolkit'
import authReducer from '../features/auth/authSlice'
import researchReducer from '../features/research/researchSlice'

export const store = configureStore({
  reducer: { auth: authReducer, research: researchReducer },
})

export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch
