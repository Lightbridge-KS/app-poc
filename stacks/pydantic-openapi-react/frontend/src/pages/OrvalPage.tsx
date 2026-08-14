import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import {
  getListStudiesQueryKey,
  useCreateReport,
  useListStudies,
  useResetDemo,
} from '../api/orval/poc'
import { Modality, type ErrorOut } from '../api/orval/model'
import { formatTime, parseStudy } from '../api/client'
import { ReportForm, StudyTable } from '../components'

/**
 * orval — the thick end of the tool table.
 *
 * Same openapi.json, same backend. What arrives instead of a type file is a
 * full SDK: named hooks, TanStack Query caching, and MSW handlers. Two
 * differences from the openapi-fetch page are worth noticing:
 *
 *  1. The hook is `useCreateReport`, not `useCreateReportStudiesStudyIdReportPost`
 *     — that name is decided by `generate_unique_id_function` in Python (gotcha #2).
 *  2. Enums arrive as a runtime *value* as well as a type, so the `<select>`
 *     below iterates `Object.values(Modality)` instead of a hand-written list.
 */
export function OrvalPage() {
  const [modality, setModality] = useState<Modality | ''>('')
  const [selected, setSelected] = useState<string | null>(null)
  const [error, setError] = useState<ErrorOut | null>(null)
  const [ok, setOk] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const studiesQuery = useListStudies(modality === '' ? undefined : { modality })
  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: getListStudiesQueryKey() })

  const createReport = useCreateReport({
    mutation: {
      onSuccess: (res) => {
        // orval's fetch client resolves on every status and discriminates on
        // it, so 201 / 404 / 409 are three separately typed branches rather
        // than one catch-all error object.
        if (res.status === 201) {
          setError(null)
          setOk(`Reported ${res.data.study_id} at ${formatTime(new Date(res.data.created_at))}`)
          void invalidate()
        } else if (res.status === 404 || res.status === 409) {
          setOk(null)
          setError(res.data)
        }
      },
    },
  })

  const resetDemo = useResetDemo({
    mutation: {
      onSuccess: () => {
        setError(null)
        setOk(null)
        setSelected(null)
        void invalidate()
      },
    },
  })

  const studies =
    studiesQuery.data?.status === 200 ? studiesQuery.data.data.map(parseStudy) : []

  return (
    <section className="stack">
      <p className="lede">
        Generated hooks over the same contract. More machinery — TanStack Query, MSW mocks —
        in exchange for caching, invalidation and named call sites.
      </p>

      <div className="toolbar">
        <label>
          Modality
          <select
            value={modality}
            onChange={(e) => setModality(e.target.value as Modality | '')}
          >
            <option value="">All</option>
            {/* The enum exists at runtime here, unlike the types-only client. */}
            {Object.values(Modality).map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </label>
        <button className="ghost" onClick={() => resetDemo.mutate()}>
          Reset demo
        </button>
        {(studiesQuery.isFetching || createReport.isPending) && (
          <span className="muted">working…</span>
        )}
      </div>

      {error && (
        <div className="error" role="alert">
          <strong>{error.code}</strong> — {error.message}
          <span className="hint">narrowed by HTTP status</span>
        </div>
      )}

      <StudyTable studies={studies} selected={selected} onSelect={setSelected} />

      {selected && (
        <ReportForm
          studyId={selected}
          busy={createReport.isPending}
          onSubmit={(findings, impression, critical) =>
            createReport.mutate({
              studyId: selected,
              // Checked against the Pydantic `ReportIn`, same as the other page.
              data: { findings, impression, critical },
            })
          }
        />
      )}

      {ok && <div className="ok">{ok}</div>}
    </section>
  )
}
