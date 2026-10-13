import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, expect, test, vi } from 'vitest'
import { getIntegrationHealth, getSavedRuns } from '../lib/api'
import HomePage from './HomePage'

vi.mock('../lib/api', async () => ({ ...await vi.importActual('../lib/api'), getIntegrationHealth: vi.fn(), getSavedRuns: vi.fn() }))
beforeEach(() => { vi.resetAllMocks(); vi.mocked(getSavedRuns).mockResolvedValue({ runs: [], limit: 5 }) })

test('states the bounded decision contract and labels sample replay before launch', async () => {
  vi.mocked(getIntegrationHealth).mockResolvedValue({ mode: 'mock', ready: true })
  render(<MemoryRouter><HomePage /></MemoryRouter>)
  expect(screen.getByRole('heading', { name: /One baseline/i })).toBeInTheDocument()
  expect(screen.getByText(/deterministic evidence selects the winner/i)).toBeInTheDocument()
  expect(screen.getByText('Compatibility')).toBeInTheDocument()
  expect(await screen.findByRole('button', { name: /Replay sample/i })).toBeEnabled()
  expect(screen.getByText(/No repository is migrated/)).toBeInTheDocument()
  expect(screen.queryByText('18 tests passing')).not.toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'How this run works' })).toBeVisible()
  expect(screen.getByText('Tavily')).toBeVisible()
  expect(screen.getByText(/No providers are called in this sample/)).toBeVisible()
})

test('keeps launch unavailable until the execution mode is known', () => {
  vi.mocked(getIntegrationHealth).mockReturnValue(new Promise(() => {}))
  render(<MemoryRouter><HomePage /></MemoryRouter>)
  expect(screen.getByRole('button', { name: /Split run/i })).toBeDisabled()
  expect(screen.getByText('Checking execution mode…')).toBeInTheDocument()
})

test('shows configuration failures without claiming provider readiness', async () => {
  vi.mocked(getIntegrationHealth).mockResolvedValue({ mode: 'live', ready: false })
  render(<MemoryRouter><HomePage /></MemoryRouter>)
  expect(await screen.findByText(/Provider access needs configuration/)).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /Split run/i })).toBeDisabled()
})


test('discovers retained live and failed runs even when starting is unavailable', async () => {
  vi.mocked(getIntegrationHealth).mockResolvedValue({ mode: 'live', ready: false })
  vi.mocked(getSavedRuns).mockResolvedValue({ limit: 5, runs: [{ id: 'saved-evidence', repo_url: 'https://github.com/owner/repo', mode: 'live', status: 'failed', created_at: '2026-10-13T00:00:00Z', updated_at: '2026-10-13T00:01:00Z', winner_id: null }] })
  render(<MemoryRouter><HomePage /></MemoryRouter>)
  const link = await screen.findByRole('link', { name: /Saved live run/ })
  expect(link).toHaveAttribute('href', '/runs/saved-evidence')
  expect(link).toHaveTextContent('failed')
  expect(link).not.toHaveTextContent('verified')
  expect(screen.getByRole('button', { name: /Split run/i })).toBeDisabled()
})
