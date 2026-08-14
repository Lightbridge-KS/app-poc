import { useState } from 'react'
import { formatTime, type ParsedStudy } from './api/client'

/**
 * Presentation shared by both pages on purpose: if the markup is identical, the
 * only thing that differs between the two tabs is the data layer, which is
 * exactly the comparison the doc's tool table is asking you to make.
 */
export function StudyTable({
  studies,
  selected,
  onSelect,
}: {
  studies: ParsedStudy[]
  selected: string | null
  onSelect: (id: string) => void
}) {
  if (studies.length === 0) return <p className="muted">No studies match.</p>

  return (
    <table className="studies">
      <thead>
        <tr>
          <th>Study</th>
          <th>Patient</th>
          <th>Modality</th>
          <th>Body part</th>
          <th>Acquired</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {studies.map((s) => (
          <tr
            key={s.id}
            onClick={() => onSelect(s.id)}
            className={s.id === selected ? 'selected' : undefined}
          >
            <td>
              <code>{s.id}</code>
            </td>
            <td>{s.patient_name}</td>
            <td>
              <span className="pill">{s.modality}</span>
            </td>
            <td>{s.body_part}</td>
            {/* A real Date, parsed once at the boundary — gotcha #3. */}
            <td className="muted">{formatTime(s.acquiredAt)}</td>
            <td>
              <span className={`status ${s.status}`}>{s.status}</span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export function ReportForm({
  studyId,
  onSubmit,
  busy,
}: {
  studyId: string
  onSubmit: (findings: string, impression: string, critical: boolean) => void
  busy: boolean
}) {
  const [findings, setFindings] = useState('')
  const [impression, setImpression] = useState('')
  const [critical, setCritical] = useState(false)

  return (
    <form
      className="report"
      onSubmit={(e) => {
        e.preventDefault()
        onSubmit(findings, impression, critical)
      }}
    >
      <h3>
        Report <code>{studyId}</code>
      </h3>
      <label>
        Findings
        <textarea
          value={findings}
          onChange={(e) => setFindings(e.target.value)}
          rows={2}
          required
        />
      </label>
      <label>
        Impression
        <textarea
          value={impression}
          onChange={(e) => setImpression(e.target.value)}
          rows={2}
          required
        />
      </label>
      <label className="inline">
        <input
          type="checkbox"
          checked={critical}
          onChange={(e) => setCritical(e.target.checked)}
        />
        Critical result
      </label>
      <button type="submit" disabled={busy}>
        Submit report
      </button>
    </form>
  )
}
