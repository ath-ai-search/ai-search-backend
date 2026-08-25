// =====================================================================
// 🎛️ SEARCH SETTINGS — the REAL synonym manager. Every pair the client
// adds here is read by the live search engine within 60 seconds.
// (The reference portal saved settings into a dead table — ours WORK.)
// =====================================================================
import { useEffect, useState } from 'react'
import { getSynonyms, addSynonym, removeSynonym } from '../api.js'
import { Panel, PageTitle, Badge, Skeleton, ExplainCard } from '../ui.jsx'

export default function SearchSettingsPage() {
  const [pairs, setPairs] = useState(null)
  const [a, setA] = useState('')
  const [b, setB] = useState('')
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')

  useEffect(() => {
    let alive = true
    getSynonyms().then(d => alive && setPairs(d.synonyms || [])).catch(() => alive && setPairs([]))
    return () => { alive = false }
  }, [])

  const say = (m) => { setMsg(m); setTimeout(() => setMsg(''), 2200) }

  const add = async (e) => {
    e.preventDefault()
    if (!a.trim() || !b.trim()) { say('⚠️ fill both words'); return }
    setBusy(true)
    try {
      const d = await addSynonym(a.trim(), b.trim())
      setPairs(d.synonyms || [])
      setA(''); setB('')
      say('✅ live in the search engine within a minute')
    } catch (ex) { say('⚠️ ' + (ex.message || 'failed')) }
    setBusy(false)
  }

  const remove = async (pa, pb) => {
    try {
      const d = await removeSynonym(pa, pb)
      setPairs(d.synonyms || [])
      say('removed')
    } catch { say('⚠️ failed') }
  }

  return (
    <div>
      <PageTitle icon="🎛️" title="Search settings"
                 desc="Teach your search new words. A synonym pair means: when shoppers search one word, products matching the other are found too." />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Panel title="➕ Add a synonym pair"
               right={msg && <span className="text-xs text-mint block truncate max-w-[45vw] lg:max-w-[18rem]">{msg}</span>}>
          <form onSubmit={add} className="flex items-center gap-2 flex-wrap">
            <input value={a} onChange={e => setA(e.target.value)} placeholder="e.g. sofa"
                   className="flex-1 min-w-[120px] rounded-xl bg-black/25 border border-white/15
                              px-3 py-2.5 text-sm outline-none focus:border-mint/60 transition" />
            <span className="text-mist">=</span>
            <input value={b} onChange={e => setB(e.target.value)} placeholder="e.g. couch"
                   className="flex-1 min-w-[120px] rounded-xl bg-black/25 border border-white/15
                              px-3 py-2.5 text-sm outline-none focus:border-mint/60 transition" />
            <button disabled={busy}
                    className="rounded-xl bg-mint/90 hover:bg-mint text-white font-bold
                               px-4 py-2.5 text-sm transition disabled:opacity-50">
              {busy ? '…' : 'Add'}</button>
          </form>
          <div className="text-[11px] text-mist mt-3">
            💡 Best source: the <b className="text-coral">💎 Found nothing</b> list on your
            Overview — every miss there is a synonym waiting to be added.
            Example: shoppers search "couch", you sell "sofa" → add the pair, sale saved.
          </div>
        </Panel>

        <Panel title="📖 Your dictionary"
               right={<Badge tone="mint">{pairs === null ? '…' : pairs.length} / 100</Badge>}>
          {pairs === null ? <Skeleton h={120} /> : pairs.length ? (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {pairs.map(([pa, pb]) => (
                <div key={`${pa}|${pb}`}
                     className="flex items-center justify-between text-sm rounded-lg px-3 py-2
                                bg-white/[0.03] border border-white/5">
                  <span><b>{pa}</b> <span className="text-mist">=</span> <b>{pb}</b></span>
                  <button onClick={() => remove(pa, pb)}
                          className="text-xs text-coral hover:underline">✕ remove</button>
                </div>
              ))}
            </div>
          ) : <div className="text-sm text-mist py-3">
                no synonyms yet — your first one takes 5 seconds</div>}
        </Panel>
      </div>

      <ExplainCard icon="📖"
        lines={[
          'This page teaches YOUR search new words — like a private dictionary for your shop.',
          'When shoppers use a word you don’t sell, connect it to a word you DO sell.',
          'It starts working on your live website in about 1 minute — no code needed.',
        ]}
        example={'Shoppers search “couch” but your products say “sofa” → add couch = sofa. Now “couch” finds every sofa — sale saved.'} />
    </div>
  )
}
