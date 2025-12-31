
import React from 'react'

export default function Scoring({ config }: { config: any }) {
  const rules = config?.scoring_rules || {}
  return (
    <div>
      <h2>Set Scoring</h2>
      <p className="muted">These are loaded from the backend /api/config. Hook up an editor later.</p>
      <pre className="code">{JSON.stringify(rules, null, 2)}</pre>
    </div>
  )
}
