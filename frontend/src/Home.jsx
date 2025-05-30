import { useState, useEffect } from 'react'
import { Link }                from 'react-router-dom'
import './Home.css'

export default function Home() {
  const [elos, setElos]       = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)

  useEffect(() => {
    fetch('http://localhost:8000/elo/top?limit=50')
      .then(res => {
        if (!res.ok) throw new Error(res.statusText)
        return res.json()
      })
      .then(data => {
        setElos(data)
        setLoading(false)
      })
      .catch(err => {
        console.error(err)
        setError(err.toString())
        setLoading(false)
      })
  }, [])

  if (loading) return <p>Loading…</p>
  if (error)   return <p className="error">{error}</p>

  return (
    <div className="container">
      <h1>Top 50 WWE Elo Rankings</h1>
      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Wrestler</th>
              <th>Elo</th>
            </tr>
          </thead>
          <tbody>
            {elos.map((row, i) => (
              <tr key={row.wrestler}>
                <td>{i + 1}</td>
                <td>
                  <Link to={`/wrestler/${encodeURIComponent(row.wrestler)}`}>
                    {row.wrestler}
                  </Link>
                </td>
                <td>{row.elo.toFixed(1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
