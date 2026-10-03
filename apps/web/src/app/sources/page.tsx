'use client'

import React, { useState } from 'react'
import { Header } from '@/components/Header'
import { Footer } from '@/components/Footer'
import { useToast } from '@/components/ui/ToastNotification'
import {
  CATALOG_SOURCES,
  EXPANSION_TARGETS,
  toFaDigits,
  type CatalogSource,
} from '@/lib/catalog'

export default function SourcesPage() {
  const { showToast } = useToast()
  const [sources, setSources] = useState<CatalogSource[]>(CATALOG_SOURCES)
  const [hidden, setHidden] = useState<Record<string, boolean>>({})

  // Suggestion form state
  const [url, setUrl] = useState('')
  const [category, setCategory] = useState<'movies' | 'games' | 'music'>('movies')
  const [name, setName] = useState('')
  const [tier, setTier] = useState('1')
  const [lang, setLang] = useState('EN')
  const [contact, setContact] = useState('')
  const [notes, setNotes] = useState('')
  const [agreed, setAgreed] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})

  // Toggle enabled
  function handleToggleEnabled(id: string) {
    setSources((prev) =>
      prev.map((s) => {
        if (s.id !== id) return s
        const next = !s.enabled
        showToast(
          `${s.name} ${next ? 'enabled — it joins the next fan-out' : 'disabled — excluded from every query'}`
        )
        return { ...s, enabled: next }
      })
    )
  }

  // Toggle hidden for me
  function handleToggleHide(id: string) {
    const s = sources.find((x) => x.id === id)
    setHidden((prev) => {
      const next = !prev[id]
      showToast(
        next
          ? `${s?.name || id} hidden — every later query skips it on this device`
          : `${s?.name || id} restored`
      )
      return { ...prev, [id]: next }
    })
  }

  // Address change
  function handleAddressChange(id: string, type: 'base' | 'mirror', val: string) {
    const s = sources.find((x) => x.id === id)
    if (val.trim() && !/^https:\/\//i.test(val.trim())) {
      showToast('Address must start with https://', 'error')
      return
    }
    setSources((prev) =>
      prev.map((item) => {
        if (item.id !== id) return item
        return type === 'base'
          ? { ...item, baseUrl: val }
          : { ...item, mirrorUrl: val }
      })
    )
    showToast(
      `${s?.name || id}: ${type === 'base' ? 'primary' : 'fallback'} saved. Configuration only — no code change needed (FR-021).`
    )
  }

  // Submit suggestion
  function handleSubmitSuggestion(e: React.FormEvent) {
    e.preventDefault()
    const errs: Record<string, string> = {}

    if (!url.trim()) {
      errs.url = 'Paste the portal address'
    } else {
      try {
        const u = new URL(url.trim())
        if (u.protocol !== 'https:' && u.protocol !== 'http:') {
          errs.url = 'Must be an HTTP(S) address'
        }
      } catch {
        errs.url = 'Not a valid URL'
      }
    }

    if (!name.trim()) {
      errs.name = 'How does the portal brand itself?'
    }

    if (contact.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(contact.trim())) {
      errs.contact = 'Not a valid email'
    }

    if (!agreed) {
      errs.agreed = 'You must confirm the unauthenticated links policy'
    }

    if (Object.keys(errs).length > 0) {
      setErrors(errs)
      return
    }

    setErrors({})
    showToast(`Submitted «${name.trim()}» to the operator review queue.`)
    // Reset form
    setUrl('')
    setName('')
    setContact('')
    setNotes('')
    setAgreed(false)
  }

  function handleClearForm() {
    setUrl('')
    setName('')
    setContact('')
    setNotes('')
    setAgreed(false)
    setErrors({})
    showToast('Form cleared')
  }

  const enabledCount = sources.filter((s) => s.enabled).length

  return (
    <>
      <Header activePage="sources" />

      <main id="main" className="wrap" style={{ paddingTop: 'calc(var(--hdr) + 34px)' }}>
        {/* Intro */}
        <section data-od-id="sources-intro">
          <div className="eyebrow">
            <span className="pill-red">Operator console</span>
            <span className="pill-ghost">Spec 001 US5 · FR-021 · 004 · 007</span>
          </div>
          <h1
            style={{
              fontSize: 'clamp(30px, 4.6vw, 52px)',
              fontWeight: 800,
              letterSpacing: '-.025em',
              marginTop: '14px',
              lineHeight: 1.02,
            }}
          >
            Source registry
          </h1>
          <p className="hero-desc" style={{ marginTop: '14px' }}>
            Each portal is a decoupled module behind one search/extract interface. Adding a source
            means a new module plus one row here — search, ranking and the interface stay untouched.
            Domain shifts are handled by following 301/302, and the live base address lives in
            configuration so a mirror change never needs a code change.
          </p>
        </section>

        {/* Expansion Status */}
        <section className="sec" data-od-id="expansion-status">
          <div className="sec-head">
            <h2>Expansion status</h2>
            <span className="sub">spec 005 · 006 request 20 portals per media type</span>
          </div>
          <div
            className="grid"
            style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}
            id="expansion"
          >
            {(['movies', 'games', 'music'] as const).map((catKey) => {
              const exp = EXPANSION_TARGETS[catKey]
              const pct = Math.round((exp.live / exp.target) * 100)
              const label =
                catKey === 'movies'
                  ? 'Movie portals'
                  : catKey === 'games'
                    ? 'Game portals'
                    : 'Music portals'

              return (
                <div
                  key={catKey}
                  className="notice"
                  style={{
                    flexDirection: 'column',
                    alignItems: 'stretch',
                    gap: '10px',
                  }}
                >
                  <strong
                    style={{
                      color: '#fff',
                      fontSize: '13px',
                      letterSpacing: '.1em',
                      textTransform: 'uppercase',
                    }}
                  >
                    {label}
                  </strong>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
                    <span style={{ fontSize: '26px', fontWeight: 800 }}>
                      {toFaDigits(exp.live)}
                    </span>
                    <span style={{ color: 'var(--muted-2)' }}>
                      of {toFaDigits(exp.target)} onboarded
                    </span>
                  </div>
                  <div className="bar">
                    <i style={{ width: `${pct}%` }}></i>
                  </div>
                  <span style={{ fontSize: '12px', color: 'var(--muted)' }}>
                    {exp.target - exp.live} still to onboard — submit them below.
                  </span>
                </div>
              )
            })}
          </div>
        </section>

        {/* Registry Table */}
        <section className="sec" data-od-id="registry-table">
          <div className="sec-head">
            <h2>Registered sources</h2>
            <span className="sub" id="regCount">
              {sources.length} sources · {enabledCount} enabled
            </span>
          </div>
          <div className="tbl-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Source</th>
                  <th>Category</th>
                  <th>Tier</th>
                  <th>Health</th>
                  <th>Primary address</th>
                  <th>Fallback mirror</th>
                  <th>Enabled</th>
                  <th>Hidden for me</th>
                </tr>
              </thead>
              <tbody id="regBody">
                {sources.map((s) => {
                  const isOff = !s.enabled
                  const stateKey = isOff ? 'off' : s.state
                  const ledClass =
                    stateKey === 'off'
                      ? 'bad'
                      : stateKey === 'warn'
                        ? 'warn'
                        : stateKey === 'ok'
                          ? 'ok'
                          : 'bad'
                  const stateLabel =
                    stateKey === 'off'
                      ? 'Disabled'
                      : stateKey === 'warn'
                        ? 'Degraded'
                        : stateKey === 'ok'
                          ? 'Answering'
                          : 'Failing'
                  const catLabel =
                    s.cat === 'movies' ? 'Movies' : s.cat === 'games' ? 'Games' : 'Music'

                  return (
                    <tr key={s.id}>
                      <td>
                        <strong>{s.name}</strong>
                        <br />
                        <span style={{ color: 'var(--muted-2)', fontSize: '12px' }}>
                          {s.notes}
                        </span>
                      </td>
                      <td>{catLabel}</td>
                      <td>
                        <span className="pill-ghost">{s.tierLabel}</span>
                      </td>
                      <td>
                        <span className="state">
                          <span className={`led ${ledClass}`}></span>
                          {stateLabel}
                        </span>
                      </td>
                      <td>
                        <input
                          className="input"
                          style={{
                            minHeight: '44px',
                            padding: '8px 12px',
                            fontSize: '13px',
                          }}
                          dir="ltr"
                          defaultValue={s.baseUrl || ''}
                          placeholder="https://live-mirror…"
                          onBlur={(e) => handleAddressChange(s.id, 'base', e.target.value)}
                          aria-label={`Primary address for ${s.name}`}
                        />
                      </td>
                      <td>
                        <input
                          className="input"
                          style={{
                            minHeight: '44px',
                            padding: '8px 12px',
                            fontSize: '13px',
                          }}
                          dir="ltr"
                          defaultValue={s.mirrorUrl || ''}
                          placeholder="https://fallback…"
                          onBlur={(e) => handleAddressChange(s.id, 'mirror', e.target.value)}
                          aria-label={`Fallback mirror for ${s.name}`}
                        />
                      </td>
                      <td>
                        <label className="switch">
                          <input
                            type="checkbox"
                            checked={s.enabled}
                            onChange={() => handleToggleEnabled(s.id)}
                          />
                          <span className="track"></span>
                          <span className="sr">Enable {s.name}</span>
                        </label>
                      </td>
                      <td>
                        <label className="switch">
                          <input
                            type="checkbox"
                            checked={Boolean(hidden[s.id])}
                            onChange={() => handleToggleHide(s.id)}
                          />
                          <span className="track"></span>
                          <span className="sr">Hide {s.name} from my results</span>
                        </label>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          <p
            style={{
              marginTop: '14px',
              color: 'var(--muted-2)',
              fontSize: '12px',
              maxWidth: '80ch',
            }}
          >
            Addresses are intentionally left blank: portal domains rotate faster than any
            configuration copy can keep up. The scraper follows 301/302 and captures the active
            domain at request time, so paste the current mirror into Primary and a known-good
            fallback into Fallback.
          </p>
        </section>

        {/* Suggest a source */}
        <section className="sec" data-od-id="suggest" id="suggest">
          <div className="sec-head">
            <h2>Suggest a source</h2>
            <span className="sub">spec 004 — operator review queue</span>
          </div>
          <form
            className="grid"
            style={{
              gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
              gap: '18px',
            }}
            id="suggestForm"
            onSubmit={handleSubmitSuggestion}
            noValidate
          >
            <div className={`field ${errors.url ? 'invalid' : ''}`} data-field="url">
              <label htmlFor="f-url">Portal URL</label>
              <input
                className="input"
                id="f-url"
                type="url"
                placeholder="https://example-portal.ir"
                dir="ltr"
                value={url}
                onChange={(e) => {
                  setUrl(e.target.value)
                  if (errors.url) setErrors((prev) => ({ ...prev, url: '' }))
                }}
              />
              <span className="err" id="e-url">
                {errors.url}
              </span>
            </div>

            <div className="field" data-field="cat">
              <label htmlFor="f-cat">Category</label>
              <select
                className="select"
                id="f-cat"
                value={category}
                onChange={(e) =>
                  setCategory(e.target.value as 'movies' | 'games' | 'music')
                }
              >
                <option value="movies">Movies &amp; series</option>
                <option value="games">Games</option>
                <option value="music">Music</option>
              </select>
              <span className="hint">
                The scraper module is only instantiated for the categories you pick.
              </span>
            </div>

            <div className={`field ${errors.name ? 'invalid' : ''}`} data-field="name">
              <label htmlFor="f-name">Portal name</label>
              <input
                className="input"
                id="f-name"
                type="text"
                placeholder="How the portal brands itself"
                value={name}
                onChange={(e) => {
                  setName(e.target.value)
                  if (errors.name) setErrors((prev) => ({ ...prev, name: '' }))
                }}
              />
              <span className="err" id="e-name">
                {errors.name}
              </span>
            </div>

            <div className="field" data-field="tier">
              <label htmlFor="f-tier">Proposed tier</label>
              <select
                className="select"
                id="f-tier"
                value={tier}
                onChange={(e) => setTier(e.target.value)}
              >
                <option value="1">Tier 1 — primary</option>
                <option value="2">Tier 2 — fallback</option>
                <option value="3">Tier 3 — experimental</option>
              </select>
              <span className="hint">
                Tier decides merge priority and which sources survive when a category degrades.
              </span>
            </div>

            <div className="field" data-field="lang">
              <label htmlFor="f-lang">Default audio track</label>
              <select
                className="select"
                id="f-lang"
                value={lang}
                onChange={(e) => setLang(e.target.value)}
              >
                <option value="EN">Original</option>
                <option value="FA-DUB">Persian dubbed</option>
                <option value="FA-SUB">Persian soft-sub</option>
              </select>
            </div>

            <div className={`field ${errors.contact ? 'invalid' : ''}`} data-field="contact">
              <label htmlFor="f-contact">Contact (optional)</label>
              <input
                className="input"
                id="f-contact"
                type="email"
                placeholder="you@example.com"
                dir="ltr"
                value={contact}
                onChange={(e) => {
                  setContact(e.target.value)
                  if (errors.contact) setErrors((prev) => ({ ...prev, contact: '' }))
                }}
              />
              <span className="err" id="e-contact">
                {errors.contact}
              </span>
            </div>

            <div className="field" data-field="notes" style={{ gridColumn: '1 / -1' }}>
              <label htmlFor="f-notes">What does it expose?</label>
              <textarea
                className="textarea"
                id="f-notes"
                placeholder="Direct links? multi-part archives? bitrate tiers? any password convention?"
                rows={3}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              ></textarea>
              <span className="err" id="e-notes"></span>
            </div>

            <div
              className={`field ${errors.agreed ? 'invalid' : ''}`}
              style={{ gridColumn: '1 / -1' }}
            >
              <label className="switch">
                <input
                  type="checkbox"
                  id="f-ok"
                  checked={agreed}
                  onChange={(e) => {
                    setAgreed(e.target.checked)
                    if (errors.agreed) setErrors((prev) => ({ ...prev, agreed: '' }))
                  }}
                />
                <span className="track"></span>
                <span
                  style={{
                    fontSize: '13px',
                    textTransform: 'none',
                    letterSpacing: 0,
                    color: 'var(--muted)',
                  }}
                >
                  I understand the aggregator only indexes publicly reachable, unauthenticated
                  links and never bypasses a paywall or a login.
                </span>
              </label>
              {errors.agreed && <span className="err">{errors.agreed}</span>}
            </div>

            <div
              style={{
                gridColumn: '1 / -1',
                display: 'flex',
                gap: '12px',
                flexWrap: 'wrap',
                alignItems: 'center',
              }}
            >
              <button className="btn btn-primary" type="submit">
                Send to review queue
              </button>
              <button
                className="btn btn-quiet"
                type="button"
                id="resetForm"
                onClick={handleClearForm}
              >
                Clear
              </button>
              <span className="hint" style={{ color: 'var(--muted-2)' }}>
                Submitted portals land in the operator queue — they stay out of every search until
                a scraper module lands and this table gains a row.
              </span>
            </div>
          </form>
        </section>

        {/* Tiers, censorship and IMDb */}
        <section className="sec" data-od-id="source-faq">
          <div className="sec-head">
            <h2>Tiers, censorship and IMDb</h2>
            <span className="sub">spec 007</span>
          </div>
          <div
            className="grid"
            style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))' }}
          >
            <div
              className="notice"
              style={{
                flexDirection: 'column',
                alignItems: 'flex-start',
                gap: '8px',
              }}
            >
              <strong style={{ color: '#fff' }}>Tier 1 — primary</strong>
              <span>
                Highest merge priority. When a Tier 1 source answers, Tier 3 is not even queried.
              </span>
            </div>
            <div
              className="notice"
              style={{
                flexDirection: 'column',
                alignItems: 'flex-start',
                gap: '8px',
              }}
            >
              <strong style={{ color: '#fff' }}>Tier 2 — fallback</strong>
              <span>
                Queried in the same fan-out, ranked below Tier 1. Carries most of the catalog when
                Tier 1 degrades.
              </span>
            </div>
            <div
              className="notice"
              style={{
                flexDirection: 'column',
                alignItems: 'flex-start',
                gap: '8px',
              }}
            >
              <strong style={{ color: '#fff' }}>Tier 3 — experimental</strong>
              <span>
                Only queried when Tier 1 and 2 return nothing for the query.
              </span>
            </div>
          </div>
          <div className="tbl-wrap" style={{ marginTop: '18px' }}>
            <table className="data">
              <thead>
                <tr>
                  <th>Filter</th>
                  <th>Default</th>
                  <th>Effect on results</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>IMDb rating floor</td>
                  <td className="mono">0.0</td>
                  <td>
                    Anything below the floor is dimmed and sorted last; the score itself is never
                    hidden.
                  </td>
                </tr>
                <tr>
                  <td>Censorship</td>
                  <td className="mono">include</td>
                  <td>
                    Switch to <em>uncensored only</em> to drop releases flagged as censored cuts, or{' '}
                    <em>exclude censored</em> to keep them out entirely.
                  </td>
                </tr>
                <tr>
                  <td>Source tier</td>
                  <td className="mono">1–3</td>
                  <td>
                    Raising the ceiling to Tier 1 cuts latency and hides fallbacks that would
                    otherwise pad the list.
                  </td>
                </tr>
                <tr>
                  <td>Per-user hiding</td>
                  <td className="mono">off</td>
                  <td>
                    A hidden source is excluded from every later query on this device, not just the
                    current one.
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        {/* Content Policy */}
        <section className="sec" data-od-id="legal" id="legal">
          <div className="sec-head">
            <h2>Content policy</h2>
            <span className="sub">what this prototype does and does not do</span>
          </div>
          <div
            className="grid"
            style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))' }}
          >
            <div
              className="notice"
              style={{
                flexDirection: 'column',
                alignItems: 'flex-start',
                gap: '8px',
              }}
            >
              <strong style={{ color: '#fff' }}>Implemented as a front end</strong>
              <span>
                Category isolation, Persian/Arabic normalisation, format segmentation, multi-part
                archive listing with gap detection, password copy, bitrate tiers, source health,
                tier filters, the assistant and this queue.
              </span>
            </div>
            <div
              className="notice"
              style={{
                flexDirection: 'column',
                alignItems: 'flex-start',
                gap: '8px',
              }}
            >
              <strong style={{ color: '#fff' }}>Not implemented here</strong>
              <span>
                No scraper module, no HTTP request to any portal, no scheduled crawl, no cache
                store. Download controls resolve to the upstream URL they would open and say so.
              </span>
            </div>
            <div
              className="notice"
              style={{
                flexDirection: 'column',
                alignItems: 'flex-start',
                gap: '8px',
              }}
            >
              <strong style={{ color: '#fff' }}>Operator&apos;s responsibility</strong>
              <span>
                Standing up live indexers against third-party portals is a separate decision with
                its own legal and ToS review. This repository stops at the interface.
              </span>
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </>
  )
}
