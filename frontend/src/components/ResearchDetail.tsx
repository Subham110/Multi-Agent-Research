import { useEffect, useState } from 'react'
import { BookOpen, ExternalLink, Radio, RefreshCw, ShieldCheck, XCircle } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useAppDispatch, useAppSelector } from '../app/hooks'
import { addLiveEvent, cancelResearch, fetchEvents, fetchJob, fetchJobs, fetchStats } from '../features/research/researchSlice'
import { connectResearchSocket } from '../utils/researchSocket'
import AgentTimeline from './AgentTimeline'

type Tab = 'activity' | 'report' | 'sources'

export default function ResearchDetail() {
  const dispatch = useAppDispatch()
  const token = useAppSelector((state) => state.auth.token)
  const { selectedJob: job, events } = useAppSelector((state) => state.research)
  const [tab, setTab] = useState<Tab>('activity')
  const [socketState, setSocketState] = useState<'open' | 'closed' | 'error'>('closed')

  useEffect(() => {
    if (!job || !token) return
    void dispatch(fetchEvents(job.id))
    const active = job.status === 'queued' || job.status === 'running'
    if (!active) {
      setSocketState('closed')
      return
    }
    const stop = connectResearchSocket(job.id, token, (event) => {
      dispatch(addLiveEvent(event))
      if (['job_completed', 'job_failed', 'job_cancelled', 'cancellation_requested'].includes(event.event_type)) {
        void dispatch(fetchJob(job.id))
        void dispatch(fetchJobs())
        void dispatch(fetchStats())
      }
    }, setSocketState)
    const poll = window.setInterval(() => void dispatch(fetchJob(job.id)), 5000)
    return () => {
      stop()
      window.clearInterval(poll)
    }
  }, [dispatch, job?.id, job?.status, token])

  useEffect(() => {
    if (job?.status === 'completed') setTab('report')
  }, [job?.status])

  if (!job) return null

  return (
    <section className="detail-card">
      <header className="detail-header">
        <div>
          <div className="detail-status-row">
            <span className={`status-pill status-${job.status}`}>{job.status}</span>
            {(job.status === 'queued' || job.status === 'running') && (
              <button className="cancel-button" onClick={() => void dispatch(cancelResearch(job.id))}>
                <XCircle size={14} /> Cancel
              </button>
            )}
          </div>
          <h2>{job.topic}</h2><p>{job.objective || 'No additional objective provided.'}</p>
        </div>
        <div className="progress-ring" style={{ '--progress': `${job.progress * 3.6}deg` } as React.CSSProperties}><span>{job.progress}%</span></div>
      </header>
      <div className="agent-strip">
        {['Researcher', 'Analyst', 'Writer', 'Critic'].map((agent) => <div key={agent} className={job.current_agent === agent ? 'current' : ''}><span>{agent[0]}</span><strong>{agent}</strong></div>)}
      </div>
      <nav className="detail-tabs">
        <button className={tab === 'activity' ? 'active' : ''} onClick={() => setTab('activity')}><Radio size={16} /> Activity</button>
        <button className={tab === 'report' ? 'active' : ''} onClick={() => setTab('report')}><BookOpen size={16} /> Report</button>
        <button className={tab === 'sources' ? 'active' : ''} onClick={() => setTab('sources')}><ShieldCheck size={16} /> Sources</button>
        <span className={`socket-state socket-${socketState}`}>{
          job.status === 'queued' || job.status === 'running'
            ? (socketState === 'open' ? 'Live' : 'Reconnecting')
            : 'Saved'
        }</span>
      </nav>
      <div className="detail-content">
        {tab === 'activity' && <AgentTimeline events={events} />}
        {tab === 'report' && (
          job.report ? <article className="report-view"><div className="quality-banner"><div><span>Quality score</span><strong>{job.report.quality_score}/100</strong></div><div><span>Citations</span><strong>{job.report.citation_count}</strong></div><div><span>Version</span><strong>v{job.report.version}</strong></div></div><ReactMarkdown remarkPlugins={[remarkGfm]}>{job.report.markdown}</ReactMarkdown></article>
            : <div className="empty-state report-wait"><RefreshCw className="spin" />The report will appear after the Critic quality gate.</div>
        )}
        {tab === 'sources' && (
          <div className="source-list">
            {!job.sources.length && <div className="empty-state">Verified sources appear after the report is finalized.</div>}
            {job.sources.map((source, index) => <article key={source.id}><div className="source-key">S{index + 1}</div><div><div className="source-meta"><span>{source.source_type}</span><span>{Math.round(source.credibility_score * 100)}% credibility</span></div><h3>{source.title}</h3><p>{source.abstract || source.excerpt}</p><a href={source.url} target="_blank" rel="noreferrer">Open source <ExternalLink size={14} /></a></div></article>)}
          </div>
        )}
      </div>
    </section>
  )
}
