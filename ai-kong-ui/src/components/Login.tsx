
import React, { useState } from 'react'
import { login } from '../services/api'

export default function Login({ onLogin }: { onLogin: (token: string) => void }) {
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('admin123')
  const [error, setError] = useState<string|null>(null)
  const [loading, setLoading] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const res = await login(username, password)
      localStorage.setItem('token', res.token)
      onLogin(res.token)
    } catch (err:any) {
      setError(err.message || 'Login failed')
    } finally { setLoading(false) }
  }

  return (
    <div className="login">
      <form onSubmit={submit} className="card">
        <h1>Sign in</h1>
        <label>Username
          <input value={username} onChange={e=>setUsername(e.target.value)} />
        </label>
        <label>Password
          <input type="password" value={password} onChange={e=>setPassword(e.target.value)} />
        </label>
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={loading}>{loading? 'Signing in...' : 'Login'}</button>
      </form>
    </div>
  )
}
