import { afterEach, expect, test, vi } from 'vitest'
import { createRun, getSavedRuns } from './api'

afterEach(() => vi.unstubAllGlobals())

test('passes an explicit project directory to the run API', async () => {
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ id: 'new-run' }) })
  vi.stubGlobal('fetch', fetchMock)
  await createRun('https://github.com/owner/repo', 'evaluation/fixtures/config')
  expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
    repo_url: 'https://github.com/owner/repo', target: 'pydantic-v2', project_path: 'evaluation/fixtures/config',
  })
})

test('omits an empty project directory to preserve default backend behavior', async () => {
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ id: 'new-run' }) })
  vi.stubGlobal('fetch', fetchMock)
  await createRun('https://github.com/owner/repo', '   ')
  expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ repo_url: 'https://github.com/owner/repo', target: 'pydantic-v2' })
})


test('requests only five recent run metadata records without creating a run', async () => {
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ runs: [], limit: 5 }) })
  vi.stubGlobal('fetch', fetchMock)
  await getSavedRuns()
  expect(fetchMock.mock.calls[0][0]).toBe('/api/runs?limit=5')
  expect(fetchMock.mock.calls[0][1].method).toBeUndefined()
})

test('sends only explicitly supplied advanced validation options', async () => {
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ id: 'new-run' }) })
  vi.stubGlobal('fetch', fetchMock)
  const options = { baseline_ref: 'a'.repeat(40), test_extras: [], behavior_probes: { cases: [{ id: 'string-case', module: 'app.models', model: 'User', payload: { name: 123 } }] } }
  await createRun('https://github.com/owner/repo', undefined, options)
  expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ repo_url: 'https://github.com/owner/repo', target: 'pydantic-v2', ...options })
})

test('rejects requests exceeding the API byte limit before sending', () => {
  const fetchMock = vi.fn()
  vi.stubGlobal('fetch', fetchMock)
  expect(() => createRun('https://github.com/owner/repo', undefined, { behavior_probes: { cases: [{ id: 'big', module: 'app', model: 'Model', payload: { content: 'é'.repeat(5000) } }] } })).toThrow('8 KiB')
  expect(fetchMock).not.toHaveBeenCalled()
})
