import { useEffect } from 'react'
import { Activity, BrainCircuit, Database, FileCheck2, LayoutDashboard, LogOut, Search, Sparkles } from 'lucide-react'
import { useAppDispatch, useAppSelector } from '../app/hooks'
import JobList from '../components/JobList'
import ResearchDetail from '../components/ResearchDetail'
import ResearchForm from '../components/ResearchForm'
import StatCard from '../components/StatCard'
import { logout } from '../features/auth/authSlice'
import { fetchJobs, fetchStats } from '../features/research/researchSlice'

export default function DashboardPage() {
  const dispatch = useAppDispatch()
  const user = useAppSelector((state) => state.auth.user)
  const { stats, selectedJob, error } = useAppSelector((state) => state.research)

  useEffect(() => {
    void dispatch(fetchJobs())
    void dispatch(fetchStats())
  }, [dispatch])

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><BrainCircuit size={24} /><span>ResearchMesh</span></div>
        <nav>
          <button className="active"><LayoutDashboard size={18} /> Research workspace</button>
          <button disabled><Search size={18} /> Evidence library</button>
          <button disabled><Database size={18} /> Team memory</button>
        </nav>
        <div className="sidebar-note"><Sparkles size={18} /><div><strong>Four-agent workflow</strong><span>Bounded reflection and quality gates</span></div></div>
        <div className="profile-card"><div className="avatar">{user?.full_name?.[0] ?? 'U'}</div><div><strong>{user?.full_name}</strong><span>{user?.tenant_slug}</span></div><button aria-label="Log out" onClick={() => dispatch(logout())}><LogOut size={17} /></button></div>
      </aside>
      <main className="workspace">
        <header className="workspace-header"><div><span className="eyebrow">AI research operations</span><h1>Research command center</h1><p>Launch, observe, and review evidence-grounded multi-agent reports.</p></div><div className="model-badge"><span className="live-dot" /> Gemini 3.6 Flash</div></header>
        {error && <div className="error-banner page-error">{error}</div>}
        <section className="stats-grid">
          <StatCard label="Research jobs" value={stats?.total_jobs ?? 0} detail="All workspace runs" icon={Activity} />
          <StatCard label="Completed" value={stats?.completed_jobs ?? 0} detail={`${stats?.running_jobs ?? 0} active now`} icon={FileCheck2} />
          <StatCard label="Average quality" value={`${stats?.average_quality_score ?? 0}`} detail="Critic + citation gate" icon={Sparkles} />
          <StatCard label="Evidence sources" value={stats?.total_sources ?? 0} detail="Stored with reports" icon={Database} />
        </section>
        <ResearchForm />
        <div className={`dashboard-grid ${selectedJob ? 'with-detail' : ''}`}><JobList />{selectedJob && <ResearchDetail />}</div>
      </main>
    </div>
  )
}
