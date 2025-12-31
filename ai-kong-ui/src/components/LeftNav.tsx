
import React, { useState } from 'react'
import { setConfig } from '../services/api'

export default function LeftNav({ token, config, onConfigChange }: { token: string, config: any, onConfigChange: (c:any)=>void }) {
  const [provider, setProvider] = useState(config?.llm?.provider || 'genaihub_langchain')
  const [model, setModel] = useState(config?.llm?.model || 'anthropic--claude-4-sonnet')
  const [maxTokens, setMaxTokens] = useState(String(config?.llm?.max_tokens || '8000'))
  const [temperature, setTemperature] = useState(String(config?.llm?.temperature || '0.2'))
  const [saving, setSaving] = useState(false)

  const save = async () => {
    setSaving(true)
    try {
      await setConfig(token, { llm: { provider, model, max_tokens: Number(maxTokens), temperature: Number(temperature) } })
      onConfigChange({ llm: { provider, model, max_tokens: Number(maxTokens), temperature: Number(temperature) }})
    } finally { setSaving(false) }
  }

  return (
    <aside className="leftnav">
      <h4>LLM Settings</h4>
      <label>Provider
        <select value={provider} onChange={e=>setProvider(e.target.value)}>
          <option value="genaihub_langchain">GenAIHub (LangChain)</option>
          <option value="openai">OpenAI</option>
          <option value="azure_openai">Azure OpenAI</option>
          <option value="anthropic">Anthropic</option>
        </select>
      </label>
      <label>Model
        <input value={model} onChange={e=>setModel(e.target.value)} />
      </label>
      <div className="grid2">
        <label>Max tokens
          <input type="number" value={maxTokens} onChange={e=>setMaxTokens(e.target.value)} />
        </label>
        <label>Temperature
          <input type="number" step="0.1" value={temperature} onChange={e=>setTemperature(e.target.value)} />
        </label>
      </div>
      <button onClick={save} disabled={saving}>{saving? 'Saving...' : 'Apply'}</button>
      <hr />
      <h4>Quick Actions</h4>
      <ul>
        <li>Switch LLM per run</li>
        <li>Persist runtime overrides</li>
        <li>Scoped correlation ID</li>
      </ul>
    </aside>
  )
}
