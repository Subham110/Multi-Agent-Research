import { useState, type FormEvent } from 'react'
import { Activity, BrainCircuit, CheckCircle2, Network, Search } from 'lucide-react'
import { useAppDispatch, useAppSelector } from '../app/hooks'
import { login } from '../features/auth/authSlice'

export default function LoginPage() {
  const dispatch = useAppDispatch()
  const { loading, error } = useAppSelector((state) => state.auth)
  const [email, setEmail] = useState('admin@example.com')
  const [password, setPassword] = useState('')
  const [tenant, setTenant] = useState('default')

  const submit = (event: FormEvent) => {
    event.preventDefault()
    void dispatch(login({ email, password, tenant_slug: tenant }))
  }

  return (
    <main className="auth-shell">
      <section className="auth-showcase">
        <div className="brand brand-large"><BrainCircuit size={30} /><span>ResearchMesh</span></div>
        <div className="showcase-copy">
          <span className="eyebrow">Multi-agent intelligence</span>
          <h1>Research that challenges itself before it reaches you.</h1>
          <p>Four specialized Gemini agents collect evidence, analyze it, write the report, and audit every important claim.</p>
          <div className="feature-grid">
            <div><Search /><strong>Grounded research</strong><span>Live web and paper evidence</span></div>
            <div><Network /><strong>LangGraph workflow</strong><span>Durable, bounded agent loops</span></div>
            <div><Activity /><strong>Live activity</strong><span>Watch tools and stages in real time</span></div>
            <div><CheckCircle2 /><strong>Quality gate</strong><span>Citation and critic validation</span></div>
          </div>
        </div>
        <p className="auth-footnote">Agent activity is visible. Private chain-of-thought is never exposed or stored.</p>
      </section>
      <section className="auth-panel">
        <form className="login-card" onSubmit={submit}>
          <div>
            <span className="eyebrow">Welcome back</span>
            <h2>Sign in to your workspace</h2>
            <p>Use the administrator account created during setup.</p>
          </div>
          <label>Email<input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></label>
          <label>Password<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} /></label>
          <label>Team slug<input value={tenant} onChange={(e) => setTenant(e.target.value)} required /></label>
          {error && <div className="error-banner">{error}</div>}
          <button className="primary-button" disabled={loading}>{loading ? 'Signing in…' : 'Sign in'}</button>
        </form>
      </section>
    </main>
  )
}
