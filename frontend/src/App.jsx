import React, { useState } from 'react'
import SearchBar from './components/SearchBar'
import ReportView from './components/ReportView'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function App() {
  const [ticker, setTicker] = useState('')
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function runReport(ticker) {
    setLoading(true)
    setError(null)
    setReport(null)  // Clear previous report
    try {
      const res = await fetch(`${API_URL}/report`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker }),
      })
      if (!res.ok) {
        const err = await res.text()
        throw new Error(err || res.statusText)
      }
      const data = await res.json()
      
      // Check if backend returned an error (invalid ticker)
      if (data.error) {
        throw new Error(data.message || 'Invalid ticker or unable to fetch data')
      }
      
      setReport(data)
    } catch (e) {
      setError(String(e))
      setReport(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header>
        <h1>LLM Stock Insights</h1>
        <p>Search a ticker to generate a concise LLM-backed company report (Yahoo/Wikipedia/YouTube).</p>
      </header>

      <SearchBar onSearch={(t) => { setTicker(t); runReport(t) }} loading={loading} />

      {error && <div className="error">{error}</div>}

      {report && <ReportView report={report} />}
    </div>
  )
}
