
import React, { useEffect, useState } from 'react'

interface Run {
  id: string
  when: string
  llm: string
  type: 'Analyze' | 'Generate'
  status: 'Success' | 'Error'
  coverage?: number
}

export default function Home() {
  const [runs, setRuns] = useState<Run[]>([])

  useEffect(()=>{
    const existing = JSON.parse(localStorage.getItem('historical_runs') || '[]')
    if (existing.length === 0) {
      const seed: Run[] = [
        { id: 'RUN-001', when: new Date().toISOString(), llm: 'anthropic--claude-4-sonnet', type: 'Generate', status: 'Success', coverage: 82 },
        { id: 'RUN-002', when: new Date(Date.now()-86400000).toISOString(), llm: 'openai-gpt-4o', type: 'Analyze', status: 'Success' },
        { id: 'RUN-003', when: new Date(Date.now()-172800000).toISOString(), llm: 'azure-openai-gpt-4o-mini', type: 'Generate', status: 'Error' },
      ]
      localStorage.setItem('historical_runs', JSON.stringify(seed))
      setRuns(seed)
    } else { setRuns(existing) }
  },[])

  return (
    <div>
      <h2>Historical Runs</h2>
      <p className="muted">This list is stored locally for now; wire to your backend later.</p>
      <table className="table">
        <thead>
          <tr>
            <th>Run ID</th><th>Date/Time</th><th>LLM</th><th>Type</th><th>Status</th><th>Coverage</th>
          </tr>
        </thead>
        <tbody>
          {runs.map(r => (
            <tr key={r.id}>
              <td>{r.id}</td>
              <td>{new Date(r.when).toLocaleString()}</td>
              <td>{r.llm}</td>
              <td>{r.type}</td>
              <td><span className={r.status === 'Success' ? 'badge success' : 'badge error'}>{r.status}</span></td>
              <td>{r.coverage ?? '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
