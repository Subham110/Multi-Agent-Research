import type { LucideIcon } from 'lucide-react'

interface Props {
  label: string
  value: string | number
  detail: string
  icon: LucideIcon
}

export default function StatCard({ label, value, detail, icon: Icon }: Props) {
  return (
    <article className="stat-card">
      <div className="stat-icon"><Icon size={20} /></div>
      <div><span>{label}</span><strong>{value}</strong><small>{detail}</small></div>
    </article>
  )
}
