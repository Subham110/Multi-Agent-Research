import { Clock3, FileText, LoaderCircle, TriangleAlert } from 'lucide-react'
import { useAppDispatch, useAppSelector } from '../app/hooks'
import { selectJob } from '../features/research/researchSlice'
import type { ResearchJob } from '../types'

const statusIcon = (job: ResearchJob) => {
  if (job.status === 'completed') return <FileText size={16} />
  if (job.status === 'failed') return <TriangleAlert size={16} />
  if (job.status === 'running' || job.status === 'queued') return <LoaderCircle className="spin" size={16} />
  return <Clock3 size={16} />
}

export default function JobList() {
  const dispatch = useAppDispatch()
  const { jobs, selectedJob, loading } = useAppSelector((state) => state.research)
  return (
    <section className="jobs-card">
      <div className="section-title"><div><h2>Recent research</h2><p>Reports and active multi-agent runs</p></div><span>{jobs.length} jobs</span></div>
      <div className="job-list">
        {loading && jobs.length === 0 && <div className="empty-state">Loading research jobs…</div>}
        {!loading && jobs.length === 0 && <div className="empty-state">No research yet. Launch your first mission above.</div>}
        {jobs.map((job) => (
          <button key={job.id} className={`job-row ${selectedJob?.id === job.id ? 'active' : ''}`} onClick={() => dispatch(selectJob(job))}>
            <div className={`status-symbol status-${job.status}`}>{statusIcon(job)}</div>
            <div className="job-main"><strong>{job.topic}</strong><span>{job.current_agent ?? job.status} · {new Date(job.created_at).toLocaleString()}</span></div>
            <div className="job-score">{job.report ? <><strong>{job.report.quality_score}</strong><span>quality</span></> : <><strong>{job.progress}%</strong><span>{job.status}</span></>}</div>
          </button>
        ))}
      </div>
    </section>
  )
}
