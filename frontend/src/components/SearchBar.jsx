import React, { useState } from 'react'

export default function SearchBar({ onSearch, loading }) {
  const [value, setValue] = useState('')

  function submit(e) {
    e.preventDefault()
    if (!value) return
    onSearch(value.trim().toUpperCase())
  }

  return (
    <form className="search" onSubmit={submit}>
      <input aria-label="ticker" placeholder="Enter ticker (e.g. AAPL)" value={value} onChange={(e) => setValue(e.target.value)} />
      <button type="submit" disabled={loading}>{loading ? 'Running...' : 'Generate'}</button>
    </form>
  )
}
