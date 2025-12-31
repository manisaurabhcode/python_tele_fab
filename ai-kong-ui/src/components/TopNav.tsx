
import React from 'react'
import { Link, useLocation } from 'react-router-dom'

export default function TopNav({ onLogout }: { onLogout: () => void }) {
  const loc = useLocation()
  const tabs = [
    { to: '/', label: 'Home' },
    { to: '/analyze', label: 'Analyse' },
    { to: '/generate', label: 'Generate' },
    { to: '/scoring', label: 'Set Scoring' },
  ]
  return (
    <header className="topnav">
      <div className="brand">AI Migration Utility</div>
      <nav>
        {tabs.map(t => (
          <Link key={t.to} to={t.to} className={loc.pathname === t.to ? 'active' : ''}>{t.label}</Link>
        ))}
      </nav>
      <button className="logout" onClick={onLogout}>Logout</button>
    </header>
  )
}
