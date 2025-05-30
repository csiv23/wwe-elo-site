import { useState, useEffect } from 'react'
import { useParams, Link }         from 'react-router-dom'

export default function Wrestler() {
  const { name } = useParams()
  const [matches, setMatches] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)

  useEffect(() => {
    fetch(`http://localhost:8000/matches?wrestler=${encodeURIComponent(name)}&limit=1000`)
      .then(r => {
        if (!r.ok) throw new Error(r.statusText)
        return r.json()
      })
      .then(data => {
        setMatches(data)
        setLoading(false)
      })
      .catch(e => {
        setError(e.toString())
        setLoading(false)
      })
  }, [name])

  if (loading) return <p>Loading…</p>
  if (error)   return <p style={{ color:'red' }}>{error}</p>

  return (
    <div style={{ padding:'1rem', maxWidth:800, margin:'0 auto' }}>
      <Link to="/">← back</Link>
      <h1>{name}'s Match History</h1>
      <div style={{ overflowX:'auto' }}>
        <table style={{ width:'100%', borderCollapse:'collapse' }}>
          <thead style={{ background:'#222', color:'#fff' }}>
            <tr>
              <th>Date</th>
              <th>Show</th>
              <th>Type</th>
              <th>Opponents</th>
              <th>Result</th>
            </tr>
          </thead>
          <tbody>
            {matches.map(m => (
              <tr key={m.id}>
                <td>{m.date}</td>
                <td>{m.show}</td>
                <td>{m.match_type || '—'}</td>
                <td>
                  {/* highlight the clicked wrestler */}
                  {m.winners.includes(name)
                    ? <strong>vs {m.losers}</strong>
                    : <span>{m.winners} vs <strong>{m.losers}</strong></span>
                  }
                </td>
                <td>{m.finish}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
