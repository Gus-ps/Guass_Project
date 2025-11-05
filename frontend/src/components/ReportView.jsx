import React, { useState } from 'react'

export default function ReportView({ report }) {
  const comp = report?.comparator || {}
  const markdown = comp.markdown || ''
  const youtubeVideos = report?.youtube_videos || []
  
  // State for collapsible sections (default: closed so user opens what they want)
  const [sectionsOpen, setSectionsOpen] = useState({
    analysis: false,
    youtube: false,
    rawData: false
  })
  
  const toggleSection = (section) => {
    setSectionsOpen(prev => ({ ...prev, [section]: !prev[section] }))
  }
  
  // Remove source citations from text (e.g., "(Yahoo)", "(Wikipedia)", etc.)
  const removeSourceCitations = (text) => {
    if (!text) return text
    // Remove patterns like (Yahoo), (Wikipedia), (YouTube), (Metrics), etc.
    return text.replace(/\s*\([A-Za-z/\s]+\)/g, '')
  }
  
  // Helper function to parse bold text within a string
  const parseBoldText = (text) => {
    if (!text || !text.includes('**')) return text
    
    const parts = []
    let lastIndex = 0
    const regex = /\*\*(.+?)\*\*/g
    let match
    
    while ((match = regex.exec(text)) !== null) {
      // Add text before the match
      if (match.index > lastIndex) {
        parts.push(text.substring(lastIndex, match.index))
      }
      // Add bold text
      parts.push(<strong key={match.index}>{match[1]}</strong>)
      lastIndex = regex.lastIndex
    }
    
    // Add remaining text after last match
    if (lastIndex < text.length) {
      parts.push(text.substring(lastIndex))
    }
    
    return parts.length > 0 ? parts : text
  }
  
  // Enhanced markdown to HTML converter with table support
  const renderMarkdown = (md) => {
    if (!md) return "No Report Provided"
    
    // Remove source citations first
    md = removeSourceCitations(md)
    
    const lines = md.split('\n')
    const result = []
    let currentList = []
    let currentTable = []
    let inTable = false
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i]
      
      // Check for table rows (contains |)
      if (line.trim().includes('|') && line.trim().startsWith('|')) {
        if (!inTable) {
          inTable = true
          currentTable = []
        }
        
        // Skip separator rows (like |---|---|)
        if (line.includes('---')) {
          continue
        }
        
        const cells = line.split('|').filter(cell => cell.trim()).map(cell => cell.trim())
        currentTable.push(cells)
        continue
      }
      
      // Close table if we were in one
      if (inTable) {
        if (currentTable.length > 0) {
          const tableElement = (
            <table key={`table-${result.length}`} className="markdown-table">
              <thead>
                <tr>
                  {currentTable[0].map((header, j) => (
                    <th key={j}>{parseBoldText(header)}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {currentTable.slice(1).map((row, rowIdx) => (
                  <tr key={rowIdx}>
                    {row.map((cell, cellIdx) => (
                      <td key={cellIdx}>{parseBoldText(cell)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )
          result.push(tableElement)
        }
        currentTable = []
        inTable = false
      }
      
      // Check if we need to close a list
      if (currentList.length > 0 && !line.trim().startsWith('-') && !line.trim().startsWith('*')) {
        result.push(<ul key={`ul-${result.length}`} className="markdown-list">{currentList}</ul>)
        currentList = []
      }
      
      // Headers
      if (line.startsWith('### ')) {
        const headerText = line.replace('### ', '')
        result.push(<h3 key={i}>{parseBoldText(headerText)}</h3>)
      } else if (line.startsWith('## ')) {
        const headerText = line.replace('## ', '')
        result.push(<h2 key={i}>{parseBoldText(headerText)}</h2>)
      } else if (line.startsWith('# ')) {
        const headerText = line.replace('# ', '')
        result.push(<h1 key={i}>{parseBoldText(headerText)}</h1>)
      }
      // List items
      else if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
        const content = line.trim().substring(2)
        currentList.push(
          <li key={i}>{parseBoldText(content)}</li>
        )
      }
      // Paragraph with text
      else if (line.trim()) {
        result.push(<p key={i}>{parseBoldText(line)}</p>)
      } else {
        result.push(<br key={i} />)
      }
    }
    
    // Close any remaining list
    if (currentList.length > 0) {
      result.push(<ul key={`ul-${result.length}`} className="markdown-list">{currentList}</ul>)
    }
    
    // Close any remaining table
    if (inTable && currentTable.length > 0) {
      const tableElement = (
        <table key={`table-${result.length}`} className="markdown-table">
          <thead>
            <tr>
              {currentTable[0].map((header, j) => <th key={j}>{header}</th>)}
            </tr>
          </thead>
          <tbody>
            {currentTable.slice(1).map((row, rowIdx) => (
              <tr key={rowIdx}>
                {row.map((cell, cellIdx) => <td key={cellIdx}>{cell}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      )
      result.push(tableElement)
    }
    
    return <div className="markdown-content">{result}</div>
  }
  
  // Check if report exists
  if (!report) {
    return (
      <div className="report-header">
        <h2>No report available</h2>
      </div>
    )
  }
  
  return (
    <div className="report">
      <div className="report-header">
        <h1>{report?.company_name } ({report?.ticker})</h1>
        <div className="meta-badges">
          {report?.metadata?.sector && <span className="badge">{report.metadata.sector}</span>}
          {report?.metadata?.industry && <span className="badge">{report.metadata.industry}</span>}
        </div>
        <div className="generated">Generated: {new Date(report?.header?.generated_at).toLocaleString()}</div>
      </div>

      {/* Investment Analysis Section - Collapsible */}
      <div className="collapsible-section">
        <div className="section-header" onClick={() => toggleSection('analysis')}>
          <h2>📊 Investment Analysis</h2>
          <span className="toggle-icon">{sectionsOpen.analysis ? '▼' : '▶'}</span>
        </div>
        {sectionsOpen.analysis && (
          <div className="section-content analysis-section">
            {renderMarkdown(markdown)}
          </div>
        )}
      </div>
      
      {/* YouTube Comments Section - Collapsible */}
      {youtubeVideos.length > 0 && (
        <div className="collapsible-section">
          <div className="section-header" onClick={() => toggleSection('youtube')}>
            <h2>💬 Top YouTube Comments</h2>
            <span className="toggle-icon">{sectionsOpen.youtube ? '▼' : '▶'}</span>
          </div>
          {sectionsOpen.youtube && (
            <div className="section-content youtube-section">
              <p className="section-description">Viewer perspectives from recent videos about {report?.company_name}</p>
              {youtubeVideos.map((video, idx) => (
                <div key={idx} className="video-comments-card">
                  <h3 className="video-title">
                    <a href={video.url} target="_blank" rel="noopener noreferrer">
                      📹 {video.title}
                    </a>
                  </h3>
                  <div className="top-comments">
                    {video.top_comments.map((comment, commentIdx) => (
                      <div key={commentIdx} className="comment">
                        <div className="comment-author">{comment.author}</div>
                        <div className="comment-text" dangerouslySetInnerHTML={{ __html: comment.text }} />
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
      
      {/* Raw Data Section - Collapsible (collapsed by default) */}
      <div className="collapsible-section">
        <div className="section-header" onClick={() => toggleSection('rawData')}>
          <h2>📈 Financial Metrics & Data</h2>
          <span className="toggle-icon">{sectionsOpen.rawData ? '▼' : '▶'}</span>
        </div>
        {sectionsOpen.rawData && (
          <div className="section-content raw-data-section">
            <h3>Key Metrics</h3>
            <pre>{report?.metrics_text || 'No metrics available'}</pre>
            
            <h3>Company Information</h3>
            <div className="metadata-grid">
              {report?.metadata?.sector && <div><strong>Sector:</strong> {report.metadata.sector}</div>}
              {report?.metadata?.industry && <div><strong>Industry:</strong> {report.metadata.industry}</div>}
              {report?.metadata?.market_cap && <div><strong>Market Cap:</strong> {report.metadata.market_cap}</div>}
              {report?.metadata?.beta && <div><strong>Beta:</strong> {report.metadata.beta}</div>}
              {report?.metadata?.trailing_pe && <div><strong>Trailing P/E:</strong> {report.metadata.trailing_pe}</div>}
              {report?.metadata?.forward_pe && <div><strong>Forward P/E:</strong> {report.metadata.forward_pe}</div>}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
