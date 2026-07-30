import { BarChart3, Bot, CheckCircle2, FilePenLine, Search, ShieldCheck, Wrench } from 'lucide-react'
import type { ResearchEvent } from '../types'

const iconFor = (event: ResearchEvent) => {
  if (event.event_type === 'tool_activity') return Wrench
  if (event.event_type === 'reflection') return ShieldCheck
  if (event.event_type === 'job_completed') return CheckCircle2
  if (event.agent === 'Researcher') return Search
  if (event.agent === 'Analyst') return BarChart3
  if (event.agent === 'Writer') return FilePenLine
  return Bot
}

export default function AgentTimeline({ events }: { events: ResearchEvent[] }) {
  if (!events.length) return <div className="empty-state activity-empty">Agent activity will appear here when the workflow starts.</div>
  return (
    <div className="timeline">
      {events.map((event, index) => {
        const Icon = iconFor(event)
        return (
          <article className="timeline-event" key={event.id ?? `${event.sequence}-${index}`}>
            <div className="timeline-marker"><Icon size={16} /></div>
            <div className="timeline-body">
              <div><strong>{event.agent ?? 'System'}</strong><span>{event.event_type.replaceAll('_', ' ')}</span></div>
              <p>{event.message}</p>
              {event.created_at && <time>{new Date(event.created_at).toLocaleTimeString()}</time>}
            </div>
          </article>
        )
      })}
    </div>
  )
}
