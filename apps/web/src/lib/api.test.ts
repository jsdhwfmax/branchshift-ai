import { afterEach, expect, test, vi } from 'vitest'
import { createRun } from './api'

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
