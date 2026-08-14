import { useCallback, useEffect, useState } from 'react'
import {
  MODALITIES,
  api,
  formatTime,
  parseStudy,
  type ErrorOut,
  type Modality,
  type ParsedStudy,
  type Report,
} from '../api/client'
import { ReportForm, StudyTable } from '../components'

/**
 * openapi-typescript + openapi-fetch.
 *
 * Every call below is checked against openapi.json. Nothing is generated except
 * `schema.d.ts` — no SDK, no hooks, no client state library.
 */
export function FetchPage() {
  const [studies, setStudies] = useState<ParsedStudy[]>([])
  const [modality, setModality] = useState<Modality | ''>('')
  const [selected, setSelected] = useState<string | null>(null)
  const [report, setReport] = useState<Report | null>(null)
  const [error, setError] = useState<ErrorOut | null>(null)
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    setBusy(true)
    // The path, and the fact that `modality` is a query param whose type is the
    // literal union, are both inferred from `paths`.
    const { data, error } = await api.GET('/studies', {
      params: { query: modality === '' ? {} : { modality } },
    })
    setBusy(false)
    if (error) return
    setStudies(data.map(parseStudy))
  }, [modality])

  useEffect(() => {
    void load()
  }, [load])

  async function submitReport(findings: string, impression: string, critical: boolean) {
    if (!selected) return
    setError(null)
    setBusy(true)
    const { data, error } = await api.POST('/studies/{study_id}/report', {
      params: { path: { study_id: selected } },
      // Type-checked field by field against the Pydantic `ReportIn`.
      body: { findings, impression, critical },
    })
    setBusy(false)
    if (error) {
      // GOTCHA #5 — this branch is narrowed to `ErrorOut` because the route
      // declares `responses={404: {"model": ErrorOut}}`. Without that it would
      // be an untyped blob and `error.message` would not compile.
      setError(error as ErrorOut)
      return
    }
    setReport(data)
    await load()
  }

  async function trigger404() {
    setReport(null)
    const { error } = await api.GET('/studies/{study_id}', {
      params: { path: { study_id: 'ST-DOES-NOT-EXIST' } },
    })
    setError(error ? (error as ErrorOut) : null)
  }

  async function reset() {
    setError(null)
    setReport(null)
    setSelected(null)
    await api.POST('/reset', {})
    await load()
  }

  return (
    <section className="stack">
      <p className="lede">
        One generated file (<code>schema.d.ts</code>) and a 6&nbsp;kb client. Call sites read
        like <code>fetch</code>, but the path, params, body and error branch are all inferred.
      </p>

      <div className="toolbar">
        <label>
          Modality
          <select
            value={modality}
            onChange={(e) => setModality(e.target.value as Modality | '')}
          >
            <option value="">All</option>
            {MODALITIES.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </label>
        <button onClick={trigger404} className="ghost">
          Trigger a typed 404
        </button>
        <button onClick={reset} className="ghost">
          Reset demo
        </button>
        {busy && <span className="muted">working…</span>}
      </div>

      {error && (
        <div className="error" role="alert">
          <strong>{error.code}</strong> — {error.message}
          <span className="hint">narrowed to ErrorOut, not `any`</span>
        </div>
      )}

      <StudyTable studies={studies} selected={selected} onSelect={setSelected} />

      {selected && <ReportForm studyId={selected} onSubmit={submitReport} busy={busy} />}

      {report && (
        <div className="ok">
          Reported <strong>{report.study_id}</strong> at {formatTime(new Date(report.created_at))}
          {report.critical && <span className="flag">CRITICAL</span>}
        </div>
      )}
    </section>
  )
}
