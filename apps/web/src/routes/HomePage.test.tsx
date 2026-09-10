import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, expect, test, vi } from 'vitest'
import { getIntegrationHealth } from '../lib/api'
import HomePage from './HomePage'

vi.mock('../lib/api', async () => ({ ...await vi.importActual('../lib/api'), getIntegrationHealth: vi.fn() }))
beforeEach(() => vi.resetAllMocks())

test('states the bounded decision contract and labels sample replay before launch', async () => {
  vi.mocked(getIntegrationHealth).mockResolvedValue({ mode: 'mock', ready: true })
  render(<MemoryRouter><HomePage /></MemoryRouter>)
  expect(screen.getByRole('heading', { name: /One baseline/i })).toBeInTheDocument()
  expect(screen.getByText(/deterministic evidence selects the winner/i)).toBeInTheDocument()
  expect(screen.getByText('Compatibility')).toBeInTheDocument()
  expect(await screen.findByRole('button', { name: /Replay sample/i })).toBeEnabled()
  expect(screen.getByText(/No repository is migrated/)).toBeInTheDocument()
  expect(screen.queryByText('18 tests passing')).not.toBeInTheDocument()
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
