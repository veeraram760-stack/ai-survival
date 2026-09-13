import { useState } from 'react'

interface AffiliateResult {
  status: string
  network?: string
  original_url?: string
  affiliate_url?: string
  campaign_id?: string
  agent_id?: string
  tracking_params?: Record<string, string>
  error?: string
}

export default function Affiliate({ apiBase }: { apiBase: string }) {
  const [network, setNetwork] = useState('amazon')
  const [productUrl, setProductUrl] = useState('https://www.amazon.com/dp/B08N5WRWNW')
  const [campaignId, setCampaignId] = useState('')
  const [agentId, setAgentId] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<AffiliateResult | null>(null)

  const generateLink = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setResult(null)
    try {
      const res = await fetch(`${apiBase}/tools/affiliate_link/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          network,
          product_url: productUrl,
          campaign_id: campaignId || undefined,
          agent_id: agentId || undefined,
        }),
      })
      const data = await res.json()
      setResult(data)
    } catch (err) {
      setResult({ status: 'failed', error: String(err) })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ padding: 24, maxWidth: 900, margin: '0 auto' }}>
      <h1 style={{ color: '#00ff88', marginBottom: 16 }}>Affiliate Link Generator</h1>
      <form onSubmit={generateLink} style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 24 }}>
        <div style={{ display: 'flex', gap: 12 }}>
          <select value={network} onChange={e => setNetwork(e.target.value)} style={{ background: '#111118', color: '#e0e0e0', border: '1px solid #2a2a35', borderRadius: 6, padding: 10 }}>
            <option value="amazon">Amazon</option>
            <option value="shareasale">ShareASale</option>
            <option value="cj">CJ Affiliate</option>
            <option value="impact">Impact</option>
            <option value="custom">Custom</option>
          </select>
          <input
            type="text"
            value={productUrl}
            onChange={e => setProductUrl(e.target.value)}
            placeholder="Product URL"
            style={{ flex: 1, background: '#111118', color: '#e0e0e0', border: '1px solid #2a2a35', borderRadius: 6, padding: 10 }}
          />
        </div>
        <div style={{ display: 'flex', gap: 12 }}>
          <input
            type="text"
            value={campaignId}
            onChange={e => setCampaignId(e.target.value)}
            placeholder="Campaign ID (optional)"
            style={{ flex: 1, background: '#111118', color: '#e0e0e0', border: '1px solid #2a2a35', borderRadius: 6, padding: 10 }}
          />
          <input
            type="text"
            value={agentId}
            onChange={e => setAgentId(e.target.value)}
            placeholder="Agent ID (optional)"
            style={{ flex: 1, background: '#111118', color: '#e0e0e0', border: '1px solid #2a2a35', borderRadius: 6, padding: 10 }}
          />
        </div>
        <button type="submit" disabled={loading} style={{ background: loading ? '#2a2a35' : '#00ff88', color: '#000', border: 'none', padding: '12px 18px', borderRadius: 6, cursor: 'pointer', fontWeight: 'bold' }}>
          {loading ? 'GENERATING...' : 'GENERATE AFFILIATE LINK'}
        </button>
      </form>

      {result && (
        <div style={{ background: '#111118', border: '1px solid #2a2a35', borderRadius: 8, padding: 20 }}>
          <div style={{ color: result.status === 'success' ? '#00ff88' : '#ff4444', fontWeight: 'bold', marginBottom: 12 }}>
            {result.status === 'success' ? 'SUCCESS' : 'FAILED'}
          </div>
          {result.status === 'success' && result.affiliate_url && (
            <div style={{ marginBottom: 12 }}>
              <div style={{ color: '#888', fontSize: 12, marginBottom: 4 }}>AFFILIATE URL</div>
              <a href={result.affiliate_url} target="_blank" rel="noreferrer" style={{ color: '#00aaff', wordBreak: 'break-all' }}>
                {result.affiliate_url}
              </a>
            </div>
          )}
          {result.original_url && (
            <div style={{ marginBottom: 12 }}>
              <div style={{ color: '#888', fontSize: 12, marginBottom: 4 }}>ORIGINAL URL</div>
              <div style={{ color: '#aaa', wordBreak: 'break-all' }}>{result.original_url}</div>
            </div>
          )}
          {result.tracking_params && (
            <div>
              <div style={{ color: '#888', fontSize: 12, marginBottom: 4 }}>TRACKING PARAMS</div>
              <pre style={{ background: '#0a0a0f', padding: 12, borderRadius: 6, color: '#e0e0e0', overflowX: 'auto' }}>
                {JSON.stringify(result.tracking_params, null, 2)}
              </pre>
            </div>
          )}
          {result.error && (
            <div style={{ color: '#ff4444' }}>{result.error}</div>
          )}
        </div>
      )}
    </div>
  )
}
