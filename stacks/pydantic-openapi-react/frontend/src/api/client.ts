import createClient from 'openapi-fetch'
import type { components, paths } from './schema'

/**
 * The thin end of the doc's tool table: types + a ~6kb client, nothing else.
 *
 * `paths` comes straight from the generated schema, so the path string, the
 * params, the request body and the response/error union are all checked at the
 * call site. There is no hand-written interface anywhere in this file.
 */
export const api = createClient<paths>({ baseUrl: '/api' })

/** Re-exported so components never reach into the generated file directly. */
export type Study = components['schemas']['Study']
export type Report = components['schemas']['Report']
export type ReportIn = components['schemas']['ReportIn']
export type ErrorOut = components['schemas']['ErrorOut']
export type Modality = components['schemas']['Modality']
export type StudyStatus = components['schemas']['StudyStatus']

/**
 * GOTCHA #4 — `Modality` is a string literal union because the Python enum
 * inherits `str`. The `satisfies` keeps this list honest: add "PET" here, or
 * typo "MR" as "MRI", and the build fails instead of the request 422-ing.
 */
export const MODALITIES = ['CT', 'MR', 'XR', 'US'] as const satisfies readonly Modality[]

/**
 * GOTCHA #3 — `acquired_at` is typed `string`, because a `datetime` crosses the
 * wire as ISO text. The decision the doc says to make once is made here: parse
 * at the boundary, so no component below this line ever sees a raw date string.
 */
export type ParsedStudy = Omit<Study, 'acquired_at'> & { acquiredAt: Date }

export function parseStudy(study: Study): ParsedStudy {
  const { acquired_at, ...rest } = study
  return { ...rest, acquiredAt: new Date(acquired_at) }
}

export function formatTime(date: Date): string {
  return date.toISOString().replace('T', ' ').slice(0, 16) + 'Z'
}
