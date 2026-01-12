import { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import './App.css'

function App() {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState('')
  const [result, setResult] = useState(null)
  const [activeTab, setActiveTab] = useState(0)
  const [healthStatus, setHealthStatus] = useState(null)
  const wsRef = useRef(null)


  const connectWebSocket = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${protocol}//${window.location.hostname}:${window.location.port}/ws`)

    ws.onopen = () => {
      console.log('WebSocket connected')
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      
      if (data.type === 'progress') {
        setProgress(data.message)
      } else if (data.type === 'result') {
        setResult(data.data)
        setLoading(false)
        setProgress('')
      } else if (data.type === 'error') {
        alert('Error: ' + data.message)
        setLoading(false)
        setProgress('')
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      setLoading(false)
      setProgress('')
    }

    ws.onclose = () => {
      console.log('WebSocket disconnected')
    }

    return ws
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!query.trim()) return

    setLoading(true)
    setResult(null)
    setActiveTab(0)
    setProgress('Connecting to council...')

    // Use WebSocket for real-time updates
    const ws = connectWebSocket()
    wsRef.current = ws

    ws.onopen = () => {
      ws.send(JSON.stringify({ query }))
    }
  }

  return (
    <div className="App">
      <header className="App-header">
        <h1>LLM Council</h1>
        <p>Collaborative AI Decision Making with Local LLMs</p>

      </header>

      <main className="main-content">
        <form onSubmit={handleSubmit} className="query-form">
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask your question to the LLM Council..."
            rows="4"
            disabled={loading}
          />
          <button type="submit" disabled={loading || !query.trim()}>
            {loading ? 'Processing...' : 'Submit to Council'}
          </button>
        </form>

        {progress && (
          <div className="progress-indicator">
            <div className="spinner"></div>
            <p>{progress}</p>
          </div>
        )}

        {result && (
          <div className="results">
            <section className="stage stage-final">
              <h2>Chairman's Final Answer</h2>
              <div className="response-card chairman">
                <ReactMarkdown>{result.stage3_final}</ReactMarkdown>
              </div>
            </section>

            <section className="stage stage-opinions">
              <h2>Stage 1: Council Member Opinions</h2>
              <div className="tabs">
                {result.stage1_responses.map((resp, idx) => (
                  <button
                    key={idx}
                    className={`tab ${activeTab === idx ? 'active' : ''}`}
                    onClick={() => setActiveTab(idx)}
                  >
                    {resp.model}
                  </button>
                ))}
              </div>
              <div className="tab-content">
                {result.stage1_responses[activeTab] && (
                  <div className="response-card">
                    <h3>{result.stage1_responses[activeTab].model}</h3>
                    <ReactMarkdown>
                      {result.stage1_responses[activeTab].response}
                    </ReactMarkdown>
                  </div>
                )}
              </div>
            </section>

            <section className="stage stage-reviews">
              <h2>Stage 2: Peer Reviews</h2>
              <div className="reviews-grid">
                {result.stage2_reviews.map((review, idx) => (
                  <div key={idx} className="response-card review">
                    <h3>{review.model} Review</h3>
                    <ReactMarkdown>{review.review}</ReactMarkdown>
                  </div>
                ))}
              </div>
            </section>
          </div>
        )}
      </main>

      <footer>
        <p>Powered by Ollama - Made by Bnyt and AI</p>
      </footer>
    </div>
  )
}

export default App
