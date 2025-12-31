
import React, { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'


type CoverageMapping = {
  apigee_policy: string
  apigee_policy_type: string
  kong_solution: string
  kong_plugin: string | null
  bundled_with?: string[]
  auto_generated?: boolean
  confidence?: number
  requires_custom_plugin?: boolean
  custom_plugin_name?: string | null
  reasoning?: string
}

type Coverage = {
  coverage_percentage?: number
  bundling_analysis?: {
    bundled_policies_count?: number
    efficiency_gain?: string | number
    total_bundles?: number
  }
  policy_mappings?: CoverageMapping[]
  total_policies?: number
  // Optional convenience if your backend also returns these derived values:
  auto_migrated?: number
  bundled_policies?: number
  bundling_efficiency?: number
  requires_custom_plugin?: number
}

type ResultPayload = {
  coverage?: Coverage
  kong_config?: any
  custom_plugins?: Record<string, string>
  migration_report?: string
  manual_steps?: any[]
  validation?: {
    is_valid?: boolean
    errors?: string[]
    warnings?: string[]
    suggestions?: string[]
    performance_notes?: string[]
    security_concerns?: string[]
    missing_policies?: string[]
  }
}

function Tile({ label, value }: { label: string; value: any }) {
  return (
    <div className="tile">
      <div className="label">{label}</div>
      <div className="value">{String(value ?? '-')}</div>
    </div>
  )
}

/** Strict tab union and labels map */
type Tab = 'coverage' | 'manual' | 'config' | 'plugins' | 'report' | 'validation'

const TABS: Tab[] = ['coverage', 'manual', 'config', 'plugins', 'report', 'validation']

const LABELS: Record<Tab, string> = {
  coverage: 'Policy Mappings',
  manual: 'Manual Steps',
  config: 'Kong Config',
  plugins: 'Custom Plugins',
  report: 'Full Report',
  validation: 'Validation'
}

export default function Generate({ token }: { token: string }) {
  const [file, setFile] = useState<File | null>(null)
  const [result, setResult] = useState<ResultPayload | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [active, setActive] = useState<Tab>('coverage')

  const submit = async () => {
    if (!file) { setError('Upload a single Apigee bundle'); return }
    setError(null)
    const form = new FormData()
    form.append('file', file)
    const res = await fetch('http://localhost:5000/api/ai-generate-migration', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: form
    })
    if (!res.ok) { const e = await res.json(); setError(e.error || 'Generate failed'); return }

    const data = await res.json() as ResultPayload
    setResult(data)

    const coveragePct = data.coverage?.coverage_percentage
    const runs = JSON.parse(localStorage.getItem('historical_runs') || '[]')
    runs.unshift({
      id: `RUN-${String(runs.length + 1).padStart(3, '0')}`,
      when: new Date().toISOString(),
      llm: 'runtime',
      type: 'Generate',
      status: 'Success',
      coverage: coveragePct
    })
    localStorage.setItem('historical_runs', JSON.stringify(runs))
  }

  const exportZip = async () => {
    if (!result) return
    const res = await fetch('http://localhost:5000/api/export-complete-package', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify(result)
    })
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'kong-migration-package.zip'
    a.click()
  }

  const cov = result?.coverage
  // derive KPI values robustly from coverage
  const kpiCoverage = cov?.coverage_percentage ?? '-'
  const kpiAuto = cov?.auto_migrated ?? (cov?.policy_mappings?.filter(m => m.auto_generated)?.length ?? '-')
  const kpiBundled =
    cov?.bundled_policies ??
    cov?.bundling_analysis?.bundled_policies_count ??
    (cov?.policy_mappings?.reduce((acc, m) => acc + ((m.bundled_with?.length || 0) > 0 ? 1 : 0), 0) || '-')
  const kpiEfficiency =
    cov?.bundling_efficiency ??
    (typeof cov?.bundling_analysis?.efficiency_gain === 'string'
      ? cov?.bundling_analysis?.efficiency_gain
      : cov?.bundling_analysis?.efficiency_gain ?? '-')
  const kpiCustom = cov?.requires_custom_plugin ?? (cov?.policy_mappings?.filter(m => m.requires_custom_plugin)?.length ?? '-')

  return (
    <div>
      <div className="flex-between">
        <h2>Generate</h2>
        <div className="flex">
          <label className="btn">
            Select ZIP
            <input type="file" accept=".zip" onChange={e => setFile(e.target.files?.[0] || null)} style={{ display: 'none' }} />
          </label>
          <button className="btn" onClick={submit}>Run AI Generate</button>
          {result && <button className="btn secondary" onClick={exportZip}>Download ZIP</button>}
        </div>
      </div>

      {error && <p className="error">{error}</p>}

      {result && (
        <>
          {/* KPIs */}
          <div className="kpi">
            <Tile label="Coverage" value={`${kpiCoverage}%`} />
            <Tile label="Auto-Migrated" value={kpiAuto} />
            <Tile label="Bundled Policies" value={kpiBundled} />
            <Tile label="Bundling Efficiency" value={typeof kpiEfficiency === 'number' ? `${kpiEfficiency}%` : kpiEfficiency} />
            <Tile label="Requires Custom Plugins" value={kpiCustom} />
          </div>

          {/* Tabs */}
          <div className="tabs">
            {TABS.map((t) => (
              <button
                key={t}
                className={['tab', active === t ? 'active' : ''].join(' ')}
                onClick={() => setActive(t)}
              >
                {LABELS[t]}
              </button>
            ))}
          </div>

          {/* Tab content: Policy Mappings */}
          {active === 'coverage' && (
            <div className="card2">
              <h3>Policy Bundling Analysis</h3>
              <p className="text-sm">
                Bundled policies: <strong>{kpiBundled}</strong>, Efficiency: <strong>{typeof kpiEfficiency === 'number' ? `${kpiEfficiency}%` : kpiEfficiency}</strong>
              </p>

              {(cov?.policy_mappings || []).map((m, idx) => (
                <div key={idx} className="card2" style={{ marginTop: 12 }}>
                  <div className="flex-between">
                    <div>
                      <div className="text-lg">
                        <strong>{m.apigee_policy}</strong> <span className="text-xs">({m.apigee_policy_type})</span>
                      </div>
                      <div className="text-sm text-muted">{m.reasoning}</div>
                    </div>
                    <div className="text-xs">
                      {m.auto_generated ? 'Auto' : 'Manual'} • {m.confidence != null ? Math.round(m.confidence * 100) : '-'}% confidence
                    </div>
                  </div>
                  <div className="text-sm">
                    <strong>Kong Solution:</strong> {m.kong_solution}
                    {m.kong_plugin && (<span style={{ marginLeft: 8 }} className="text-xs">[{m.kong_plugin}]</span>)}
                    {m.requires_custom_plugin && m.custom_plugin_name && (
                      <span style={{ marginLeft: 8 }} className="text-xs">• Custom: {m.custom_plugin_name}</span>
                    )}
                  </div>
                  {m.bundled_with && m.bundled_with.length > 0 && (
                    <div className="text-xs text-muted" style={{ marginTop: 6 }}>
                      Bundled with: {m.bundled_with.join(', ')}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Tab content: Manual Steps */}
          {active === 'manual' && (
            <div className="card2">
              <h3>Manual Steps</h3>
              <p className="text-sm text-muted">Tasks that require manual changes or reviews.</p>
              {(result?.manual_steps || []).length === 0 && <p className="text-sm">No manual steps detected.</p>}
              {(result?.manual_steps || []).map((s: any, idx: number) => (
                <div key={idx} className="card2" style={{ marginTop: 12 }}>
                  <div className="text-lg">
                    <strong>{s.title || (`Step ${idx + 1}`)}</strong>{' '}
                    <span className="text-xs">{s.priority || 'medium'}</span>
                  </div>
                  <div className="text-sm">{s.description || ''}</div>
                </div>
              ))}
            </div>
          )}

          {/* Tab content: Kong Config */}
          {active === 'config' && (
            <div className="card2">
              <div className="flex-between">
                <h3>Kong decK Configuration</h3>
                <button className="btn ghost" onClick={() => navigator.clipboard.writeText(JSON.stringify(result?.kong_config, null, 2))}>
                  Copy JSON
                </button>
              </div>
              <pre className="code mono">{JSON.stringify(result?.kong_config, null, 2)}</pre>
            </div>
          )}

          {/* Tab content: Custom Plugins */}
          {active === 'plugins' && (
            <div className="card2">
              <h3>Custom Plugins</h3>
              {Object.keys(result?.custom_plugins || {}).length === 0 && (<p className="text-sm">No custom plugins required.</p>)}
              {Object.entries(result?.custom_plugins || {}).map(([name, content]) => (
                <div key={name} className="card2" style={{ marginTop: 12 }}>
                  <div className="text-lg"><strong>{name}</strong></div>
                  <pre className="code mono">{String(content).substring(0, 1500)}{String(content).length > 1500 ? '...' : ''}</pre>
                </div>
              ))}
            </div>
          )}

          {/* Tab content: Full Report */}
          
          {active === 'report' && (
            <div className="card2">
              <div className="flex-between">
                <h3>Full Report</h3>
                <div className="flex" style={{ gap: 8 }}>
                  <button
                    className="btn ghost"
                    onClick={() => navigator.clipboard.writeText(result?.migration_report ?? '')}
                  >
                    Copy Markdown
                  </button>
                  <button
                    className="btn ghost"
                    onClick={() => {
                      const blob = new Blob([result?.migration_report ?? ''], { type: 'text/markdown' })
                      const url = URL.createObjectURL(blob)
                      const a = document.createElement('a')
                      a.href = url
                      a.download = 'MIGRATION_REPORT.md'
                      a.click()
                    }}
                  >
                    Download .md
                  </button>
                </div>
              </div>

              {/* Render Markdown with GFM */}
              <div className="prose" style={{ maxWidth: '100%' }}>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {result?.migration_report ?? ''}
                </ReactMarkdown>
              </div>
            </div>
          )}


          {/* Tab content: Validation */}
          {active === 'validation' && (
            <div className="card2">
              <h3>Validation</h3>
              <div
                className={['card2', (result?.validation?.is_valid ? 'bg-green-50' : 'bg-yellow-50')].join(' ')}
                style={{ borderColor: result?.validation?.is_valid ? '#86efac' : '#fde68a' }}
              >
                <div className="text-lg">
                  {result?.validation?.is_valid ? 'Configuration Valid' : 'Review Required'}
                </div>
                {(result?.validation?.errors || []).length > 0 && (
                  <>
                    <div className="text-sm" style={{ marginTop: 8 }}><strong>Errors:</strong></div>
                    <ul className="list">
                      {(result?.validation?.errors || []).map((e, i) => (<li key={i}>• {e}</li>))}
                    </ul>
                  </>
                )}
              </div>

              {(result?.validation?.warnings || []).length > 0 && (
                <>
                  <div className="text-sm" style={{ marginTop: 12 }}><strong>Warnings:</strong></div>
                  <ul className="list">
                    {(result?.validation?.warnings || []).map((w, i) => (<li key={i}>• {w}</li>))}
                  </ul>
                </>
              )}

              {(result?.validation?.suggestions || []).length > 0 && (
                <>
                  <div className="text-sm" style={{ marginTop: 12 }}><strong>Suggestions:</strong></div>
                  <ul className="list">
                    {(result?.validation?.suggestions || []).map((w, i) => (<li key={i}>• {w}</li>))}
                  </ul>
                </>
              )}

              {(result?.validation?.performance_notes || []).length > 0 && (
                <>
                  <div className="text-sm" style={{ marginTop: 12 }}><strong>Performance Notes:</strong></div>
                  <ul className="list">
                    {(result?.validation?.performance_notes || []).map((w, i) => (<li key={i}>• {w}</li>))}
                  </ul>
                </>
              )}

              {(result?.validation?.security_concerns || []).length > 0 && (
                <>
                  <div className="text-sm" style={{ marginTop: 12 }}><strong>Security Concerns:</strong></div>
                  <ul className="list">
                    {(result?.validation?.security_concerns || []).map((w, i) => (<li key={i}>• {w}</li>))}
                  </ul>
                </>
              )}

              {(result?.validation?.missing_policies || []).length > 0 && (
                <>
                  <div className="text-sm" style={{ marginTop: 12 }}><strong>Missing/Partially Covered Policies:</strong></div>
                  <ul className="list">
                    {(result?.validation?.missing_policies || []).map((w, i) => (<li key={i}>• {w}</li>))}
                  </ul>
                </>
              )}
            </div>
          )}
        </>
      )}

      {!result && (
        <p className="text-muted">Select a proxy ZIP and click <strong>Run AI Generate</strong> to see coverage, bundling, config, report, and validation.</p>
      )}
    </div>
  )
}
