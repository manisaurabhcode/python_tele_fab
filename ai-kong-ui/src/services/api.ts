
export async function login(username: string, password: string) {
  const res = await fetch('http://localhost:5000/api/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  })
  if (!res.ok) throw new Error((await res.json()).error || 'Login failed')
  return await res.json()
}

export async function getConfig(token: string | null) {
  const res = await fetch('http://localhost:5000/api/config', {
    headers: token? { 'Authorization': `Bearer ${token}` } : {}
  })
  if (!res.ok) throw new Error('Failed to load config')
  return await res.json()
}

export async function setConfig(token: string, payload: any) {
  const res = await fetch('http://localhost:5000/api/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
    body: JSON.stringify(payload)
  })
  if (!res.ok) throw new Error('Failed to save config')
  return await res.json()
}
