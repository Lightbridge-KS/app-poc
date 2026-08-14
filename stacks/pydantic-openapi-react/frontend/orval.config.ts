import { defineConfig } from 'orval'

// The thick end of the doc's tool table: orval reads the same openapi.json and
// emits a full SDK — named hooks, TanStack Query wiring, and MSW handlers.
//
// The hook names come straight from the spec's operationId, which is why
// `generate_unique_id_function` on the Python side (gotcha #2) is what decides
// whether this file gives you `useCreateReport` or
// `useCreateReportStudiesStudyIdReportPost`.
export default defineConfig({
  poc: {
    input: '../openapi.json',
    output: {
      mode: 'split',
      target: 'src/api/orval/poc.ts',
      schemas: 'src/api/orval/model',
      client: 'react-query',
      httpClient: 'fetch',
      baseUrl: '/api',
      mock: true,
      clean: true,
      prettier: false,
      // No `query.useQuery` override here on purpose: orval's defaults map GET
      // to useQuery and POST/PUT to useMutation. Forcing useQuery globally
      // turns `createReport` into a request that fires on render.
    },
  },
})
