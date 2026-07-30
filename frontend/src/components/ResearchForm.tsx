import { useState, type FormEvent } from 'react'
import { ArrowRight, Link2, Sparkles } from 'lucide-react'
import { useAppDispatch, useAppSelector } from '../app/hooks'
import { createResearch } from '../features/research/researchSlice'
import type { ResearchDepth } from '../types'

export default function ResearchForm() {
  const dispatch = useAppDispatch()
  const creating = useAppSelector((state) => state.research.creating)
  const [topic, setTopic] = useState('')
  const [objective, setObjective] = useState('')
  const [depth, setDepth] = useState<ResearchDepth>('standard')
  const [urls, setUrls] = useState('')

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const focusUrls = urls.split(/[\n,]/).map((url) => url.trim()).filter(Boolean)
    const result = await dispatch(createResearch({
      topic,
      objective,
      depth,
      max_reflections: depth === 'quick' ? 1 : 2,
      max_revisions: depth === 'deep' ? 3 : 2,
      focus_urls: focusUrls,
    }))
    if (createResearch.fulfilled.match(result)) {
      setTopic('')
      setObjective('')
      setUrls('')
    }
  }

  return (
    <form className="research-composer" onSubmit={submit}>
      <div className="composer-heading">
        <div className="spark-icon"><Sparkles size={20} /></div>
        <div><h2>Start a research mission</h2><p>Describe the question and the decision this report should support.</p></div>
      </div>
      <label>Research topic<textarea value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="Example: How will small language models change enterprise AI costs over the next three years?" required minLength={5} /></label>
      <label>Objective and required outcome<textarea className="small-textarea" value={objective} onChange={(e) => setObjective(e.target.value)} placeholder="Audience, scope, comparison criteria, geography, time period, or decisions to support." /></label>
      <div className="depth-row">
        {(['quick', 'standard', 'deep'] as ResearchDepth[]).map((option) => (
          <button type="button" key={option} onClick={() => setDepth(option)} className={`depth-option ${depth === option ? 'selected' : ''}`}>
            <strong>{option[0].toUpperCase() + option.slice(1)}</strong>
            <span>{option === 'quick' ? 'Fast overview' : option === 'standard' ? 'Balanced depth' : 'Maximum evidence'}</span>
          </button>
        ))}
      </div>
      <label><span className="label-with-icon"><Link2 size={15} /> Focus URLs (optional)</span><textarea className="tiny-textarea" value={urls} onChange={(e) => setUrls(e.target.value)} placeholder="One URL per line. The agent treats page text as evidence, not instructions." /></label>
      <div className="composer-footer">
        <span>Researcher → Analyst → Writer → Critic</span>
        <button className="primary-button compact" disabled={creating}>{creating ? 'Starting…' : <>Launch agents <ArrowRight size={17} /></>}</button>
      </div>
    </form>
  )
}
