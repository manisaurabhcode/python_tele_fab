
import React, { useEffect, useState } from 'react'
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import TopNav from './components/TopNav'
import LeftNav from './components/LeftNav'
import Login from './components/Login'
import Home from './pages/Home'
import Analyze from './pages/Analyze'
import Generate from './pages/Generate'
import Scoring from './pages/Scoring'
import { getConfig } from './services/api'

export default function App() {
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'))
  const [config, setConfig] = useState<any>(null)
  const navigate = useNavigate()

  useEffect(() => {
    const fetchCfg = async () => {
      try { setConfig(await getConfig(token)) } catch {}
    }
    fetchCfg()
  }, [token])

  const onLogout = () => {
    localStorage.removeItem('token')
    setToken(null)
    navigate('/login')
  }

  if (!token) {
    return (
      <Routes>
        <Route path="/login" element={<Login onLogin={(t) => { setToken(t); navigate('/'); }} />} />
        <Route path="*" element={<Navigate to="/login" />} />
      </Routes>
    )
  }

  return (
    <div className="layout">
      <TopNav onLogout={onLogout} />
      <div className="content">
        <LeftNav token={token} config={config} onConfigChange={setConfig} />
        <main>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/analyze" element={<Analyze token={token} />} />
            <Route path="/generate" element={<Generate token={token} />} />
            <Route path="/scoring" element={<Scoring config={config} />} />
            <Route path="*" element={<Navigate to="/" />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}
