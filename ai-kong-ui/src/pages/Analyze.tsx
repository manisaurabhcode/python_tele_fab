
import React, { useState } from 'react'

function stripFences(s: string): string {
  if (!s) return s
  const trimmed = s.trim()
  if (trimmed.startsWith('```')) {
    return trimmed.replace(/^```[a-zA-Z]*\n/, '').replace(/\n```$/, '')
  }
  return s
}

export default function Analyze({ token }: { token: string }) {
  const [files, setFiles] = useState<FileList | null>(null)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  const submit = async () => {
    if (!files || files.length === 0) { setError('Upload one or more Apigee bundles'); return }
    setError(null)
    const form = new FormData()
    Array.from(files).forEach(f => form.append('files', f))
    const res = await fetch('http://localhost:5000/api/analyze', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: form
    })
    if (!res.ok) { const e = await res.json(); setError(e.error || 'Analyze failed'); return }
    const data = await res.json()

    // The backend typically returns { analysis: <object> }
    // but in case analysis is a fenced JSON string, handle that too.
    const raw = data?.analysis
    try {
      const parsed =
        typeof raw === 'string'
          ? JSON.parse(stripFences(raw))
          : raw
      setResult({ analysis: parsed })
    } catch (e: any) {
      // Fall back to what we received
      setResult({ analysis: raw })
    }
  }

  const a = result?.analysis

  return (
    <div>
      <div className="flex-between">
        <h2>Analyse</h2>
        <div className="flex">
          <label className="btn ghost">
            Select ZIPs
            <input
              type="file"
              multiple
              accept=".zip"
              onChange={e => setFiles(e.target.files)}
              style={{ display: 'none' }}
            />
          </label>
          <button className="btn" onClick={submit}>Analyze uploaded bundles</button>
        </div>
      </div>

      {error && <p className="error">{error}</p>}

      {!a && (
        <p className="text-muted">
          Upload one or more Apigee proxy bundles (ZIP) and click <strong>Analyze uploaded bundles</strong>.
        </p>
      )}

      {a && (
        <div className="grid cols-2">
          <section className="card2">
            <h3>Proxy Overview</h3>
            <ul className="list">
              <li><strong>Name:</strong> {a.proxy_overview?.name}</li>
              <li><strong>Base path:</strong> {a.proxy_overview?.base_path}</li>
              <li><strong>Target endpoint:</strong> {a.proxy_overview?.target_endpoint}</li>
              <li><strong>Description:</strong> {a.proxy_overview?.description}</li>
              <li><strong>Complexity:</strong> {a.proxy_overview?.complexity}</li>
              <li><strong>Reason:</strong> {a.proxy_overview?.complexity_reason}</li>
            </ul>
          </section>

          <section className="card2">
            <h3>Security</h3>
            <p className="text-sm"><strong>Authentication:</strong> {a.security?.authentication}</p>
            <p className="text-sm"><strong>Authorization:</strong> {a.security?.authorization}</p>
            <p className="text-sm"><strong>Threat Protection:</strong></p>
            <ul className="list">
              {(a.security?.threat_protection || []).map((t: string, i: number) => (<li key={i}>• {t}</li>))}
            </ul>
          </section>

          <section className="card2" style={{ gridColumn: '1 / -1' }}>
            <h3>Policies Analysis ({(a.policies_analysis || []).length})</h3>
            {(a.policies_analysis || []).map((p: any, idx: number) => (
              <div key={idx} className="card2" style={{ marginTop: 12 }}>
                <div className="flex-between">
                  <div>
                    <div className="text-lg"><strong>{p.policy_name}</strong> <span className="text-xs">({p.policy_type})</span></div>
                    <div className="text-sm text-muted">{p.purpose}</div>
                  </div>
                  <div className="text-xs">{p.can_be_bundled ? 'Bundle candidate' : 'Standalone'}</div>
                </div>
                <div className="grid cols-2" style={{ marginTop: 8 }}>
                  <div>
                    <div className="text-sm"><strong>Configuration</strong></div>
                    <pre className="code mono">{JSON.stringify(p.configuration, null, 2)}</pre>
                  </div>
                  <div>
                    <div className="text-sm"><strong>Dependencies</strong></div>
                    <ul className="list">{(p.dependencies || []).map((d: string, i: number) => (<li key={i}>• {d}</li>))}</ul>
                    <div className="text-sm"><strong>Bundling candidates</strong></div>
                    <ul className="list">{(p.bundling_candidates || []).map((d: string, i: number) => (<li key={i}>• {d}</li>))}</ul>
                  </div>
                </div>
              </div>
            ))}
          </section>

          <section className="card2" style={{ gridColumn: '1 / -1' }}>
            <h3>Flows ({(a.flows || []).length})</h3>
            {(a.flows || []).map((f: any, idx: number) => (
              <div key={idx} className="card2" style={{ marginTop: 12 }}>
                <div className="text-lg"><strong>{f.flow_name}</strong></div>
                <div className="text-sm"><strong>Condition:</strong> {f.condition}</div>
                <div className="text-sm"><strong>Policies:</strong> {(f.policies || []).join(', ')}</div>
              </div>
            ))}
          </section>

          <section className="card2" style={{ gridColumn: '1 / -1' }}>
            <h3>Bundling Opportunities</h3>
            {(a.bundling_opportunities || []).map((b: any, idx: number) => (
              <div key={idx} className="card2" style={{ marginTop: 12 }}>
                <div className="text-lg"><strong>{b.bundle_name}</strong></div>
                <div className="text-sm"><strong>Policies:</strong> {(b.policies || []).join(', ')}</div>
                <div className="text-sm"><strong>Reason:</strong> {b.reason}</div>
                <div className="text-sm"><strong>Single plugin:</strong> {b.single_plugin}</div>
              </div>
            ))}
          </section>
        </div>
      )}
    </div>
  )
}
