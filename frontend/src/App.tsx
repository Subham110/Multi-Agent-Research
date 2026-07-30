import { Navigate, Route, Routes } from 'react-router-dom'
import { useAppSelector } from './app/hooks'
import DashboardPage from './pages/DashboardPage'
import LoginPage from './pages/LoginPage'

export default function App() {
  const token = useAppSelector((state) => state.auth.token)
  return (
    <Routes>
      <Route path="/login" element={token ? <Navigate to="/" replace /> : <LoginPage />} />
      <Route path="/*" element={token ? <DashboardPage /> : <Navigate to="/login" replace />} />
    </Routes>
  )
}
