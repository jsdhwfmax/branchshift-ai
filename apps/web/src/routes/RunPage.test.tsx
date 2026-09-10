import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useNavigate } from 'react-router-dom'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { getRun, type BranchResult, type RunEvent, type RunSummary } from '../lib/api'
import RunPage from './RunPage'

vi.mock('../lib/api', async () => ({ ...await vi.importActual('../lib/api'), getRun: vi.fn() }))

class TestEventSource extends EventTarget {
  static instances: TestEventSource[] = []
  onopen: (() => void) | null = null
  onerror: (() => void) | null = null
  close = vi.fn()
  constructor(public url: string) { super(); TestEventSource.instances.push(this) }
  emit(type: string, changes: Partial<RunEvent> = {}) {
    this.dispatchEvent(new MessageEvent(type, { data: JSON.stringify({
      id: 1, run_id: 'run-one', type, message: 'A recorded event',
      created_at: '2026-09-10T00:00:00Z', branch_id: null, payload: {}, ...changes,
    }) }))
  }
}

const sampleRun = (changes: Partial<RunSummary> = {}): RunSummary => ({
  id: 'run-one', repo_url: 'https://github.com/owner/repo', target: 'pydantic-v2',
  mode: 'live', status: 'queued', created_at: '2026-09-10T00:00:00Z', updated_at: '2026-09-10T00:00:00Z',
  strategies: [], branches: [], citations: [], winner_id: null, patch: null, report: null, failure_reason: null,
  ...changes,
})
const result = (changes: Partial<BranchResult> = {}): BranchResult => ({
  strategy_id: 'minimal', status: 'passed', tests_collected: 18, tests_passed: 18, tests_failed: 0,
  pip_check_passed: true, lint_findings: 0, changed_files: 2, changed_lines: 15,
  elapsed_seconds: 5, patch_applicable: true,
  pydantic_major: 2, test_exit_code: 0, pip_exit_code: 0, test_contract_preserved: true,
  checkpoint_id: 'child-minimal-abcdefgh', ...changes,
})

function renderRun() {
  return render(<MemoryRouter initialEntries={['/runs/run-one']}><Routes><Route path="/runs/:runId" element={<RunPage />} /></Routes></MemoryRouter>)
}
async function source() {
  await waitFor(() => expect(TestEventSource.instances.length).toBeGreaterThan(0))
  return TestEventSource.instances.at(-1)!
}

beforeEach(() => {
  vi.resetAllMocks()
  TestEventSource.instances = []
  vi.stubGlobal('EventSource', TestEventSource)
})
afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers() })

test('keeps one stream across status changes, deduplicates events, and clears reconnect notices', async () => {
  let current = sampleRun()
  vi.mocked(getRun).mockImplementation(async () => current)
  renderRun()
  const stream = await source()
  expect(await screen.findByRole('heading', { name: 'Run queued.' })).toBeInTheDocument()

  current = sampleRun({ status: 'branching' })
  act(() => { stream.emit('run.status'); stream.emit('run.status') })
  expect(await screen.findByRole('heading', { name: 'Branches in motion.' })).toBeInTheDocument()
  expect(screen.getAllByText('A recorded event')).toHaveLength(1)
  expect(TestEventSource.instances).toHaveLength(1)
  expect(stream.close).not.toHaveBeenCalled()

  act(() => stream.onerror?.())
  expect(screen.getByText(/Reconnecting automatically/)).toBeInTheDocument()
  act(() => stream.onopen?.())
  await waitFor(() => expect(screen.queryByText(/Reconnecting automatically/)).not.toBeInTheDocument())

  current = sampleRun({ status: 'completed', winner_id: 'minimal', branches: [result()], patch: '+ migrated', revalidated_checkpoint_id: 'clean-baseline-abcdefgh' })
  act(() => stream.emit('run.completed', { id: 2 }))
  expect(await screen.findByRole('heading', { name: 'Migration verified.' })).toBeInTheDocument()
  expect(stream.close).toHaveBeenCalledTimes(1)
  expect(TestEventSource.instances).toHaveLength(1)
  expect(screen.getByLabelText('Clean revalidation checkpoint')).toHaveTextContent('clean-baseli…')
  expect(screen.getByTitle('child-minimal-abcdefgh')).toHaveTextContent('child-minima…')
  expect(within(screen.getByRole('table')).getByText('preserved')).toBeInTheDocument()
})

test('retains partial event evidence and renders failure and timeout reasons', async () => {
  let current = sampleRun({ status: 'branching' })
  vi.mocked(getRun).mockImplementation(async () => current)
  renderRun()
  const stream = await source()
  act(() => stream.emit('branch.completed', { branch_id: 'minimal', payload: { result: result() } }))
  await waitFor(() => expect(within(screen.getByRole('table')).getByText('18/18')).toBeInTheDocument())

  current = sampleRun({ status: 'failed', failure_reason: 'Sandbox execution exceeded its deadline.', branches: [
    result({ strategy_id: 'refactor', status: 'timed_out', tests_collected: 0, tests_passed: 0, patch_applicable: false, failure_reason: 'Refactor timed out after 120 seconds.' }),
  ] })
  act(() => stream.emit('run.failed', { id: 2, message: 'Run stopped at its deadline' }))
  expect(await screen.findByRole('heading', { name: 'Run stopped.' })).toBeInTheDocument()
  expect(screen.getByRole('alert')).toHaveTextContent('Sandbox execution exceeded its deadline.')
  expect(screen.getByText('Refactor timed out after 120 seconds.')).toBeInTheDocument()
  const table = screen.getByRole('table')
  expect(within(table).getByText('18/18')).toBeInTheDocument()
  expect(within(table).getByText('timed out')).toBeInTheDocument()
  expect(within(table).queryByText('0/0')).not.toBeInTheDocument()
  expect(screen.queryByText('verified winner')).not.toBeInTheDocument()
  expect(screen.queryByText('running')).not.toBeInTheDocument()
  expect(screen.getByText('No winning patch is available for this run.')).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Download live evidence (JSON)' })).toHaveAttribute('href', '/api/runs/run-one/report')
  expect(screen.getByRole('link', { name: 'Download live evidence (JSON)' })).toHaveAttribute('download')
})

test('labels completed mock metrics, patch, and events as illustrative samples', async () => {
  vi.mocked(getRun).mockResolvedValue(sampleRun({ mode: 'mock', status: 'completed', winner_id: 'minimal', branches: [result()], patch: '+ sample', report: 'The patch was verified in a sandbox.' }))
  renderRun()
  await source()
  expect(await screen.findByRole('heading', { name: 'Sample replay complete.' })).toBeInTheDocument()
  expect(screen.getByLabelText('Execution evidence scope')).toHaveTextContent('No providers were called')
  expect(screen.queryByText('Migration verified.')).not.toBeInTheDocument()
  expect(screen.queryByText('verified winner')).not.toBeInTheDocument()
  expect(screen.queryByText('The patch was verified in a sandbox.')).not.toBeInTheDocument()
  expect(screen.getByText(/Illustrative sample metrics/)).toBeInTheDocument()
  expect(screen.getByText(/Illustrative sample patch/)).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'Sample event ledger' })).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Download sample evidence (JSON)' })).toHaveAttribute('href', '/api/runs/run-one/report')
  expect(screen.queryByText('Child checkpoint')).not.toBeInTheDocument()
})

test('does not call a completed live result verified without recorded Pydantic v2 evidence', async () => {
  vi.mocked(getRun).mockResolvedValue(sampleRun({ status: 'completed', winner_id: 'minimal', branches: [result({ pydantic_major: null })], patch: '+ candidate' }))
  renderRun()
  expect(await screen.findByRole('heading', { name: 'Run complete.' })).toBeInTheDocument()
  expect(screen.queryByText('verified winner')).not.toBeInTheDocument()
  expect(screen.getByText(/retained evidence does not establish/)).toBeInTheDocument()
})

test.each([false, null])('requires a preserved test contract before marking a live winner verified (%s)', async (preserved) => {
  vi.mocked(getRun).mockResolvedValue(sampleRun({ status: 'completed', winner_id: 'minimal', branches: [result({ test_contract_preserved: preserved })], patch: '+ candidate' }))
  renderRun()
  expect(await screen.findByRole('heading', { name: 'Run complete.' })).toBeInTheDocument()
  expect(screen.queryByText('verified winner')).not.toBeInTheDocument()
  expect(screen.queryByText('winner')).not.toBeInTheDocument()
  expect(screen.queryByText('minimal ★')).not.toBeInTheDocument()
  const contractCell = within(screen.getByRole('table')).getByText(preserved === false ? 'changed' : 'unknown')
  expect(contractCell).toBeInTheDocument()
  if (preserved === false) {
    expect(contractCell).toHaveClass('contract-changed')
    expect(screen.getByText('changed · ineligible')).toBeInTheDocument()
  } else {
    expect(contractCell).not.toHaveClass('contract-changed')
    expect(screen.getAllByTitle('The contract check did not produce a result.')).toHaveLength(2)
    expect(screen.queryByText(/changed/i)).not.toBeInTheDocument()
  }
})

test.each([
  [9.717801987, '9.7s'],
  [61.25, '1m 1s'],
  [3599.96, '1h 0m'],
])('formats elapsed time consistently in live branch metrics and evidence (%s)', async (seconds, label) => {
  vi.mocked(getRun).mockResolvedValue(sampleRun({ status: 'failed', branches: [result({ elapsed_seconds: seconds, status: 'failed' })] }))
  renderRun()
  expect(await screen.findByRole('heading', { name: 'Run stopped.' })).toBeInTheDocument()
  expect(screen.getAllByText(label)).toHaveLength(2)
  expect(within(screen.getByRole('table')).getByText(label)).toBeInTheDocument()
  expect(screen.queryByText(`${seconds}s`)).not.toBeInTheDocument()
})

test('shows actual baseline checkpoint, commit, test count, and model from a live run', async () => {
  vi.mocked(getRun).mockResolvedValue(sampleRun({ baseline_checkpoint_id: 'checkpoint-abcdefgh123', baseline_commit_sha: 'abc1234567890123456789', baseline_tests_collected: 13, model_id: 'nvidia/nemotron', baseline_test_contract_digest: 'contractdigest12345678' }))
  renderRun()
  expect(await screen.findByText('13 baseline tests')).toBeInTheDocument()
  expect(screen.getByText('Checkpoint')).toBeInTheDocument()
  expect(screen.getByTitle('checkpoint-abcdefgh123')).toHaveTextContent('checkpoint-a…')
  expect(screen.getByText('abc123456789')).toBeInTheDocument()
  expect(screen.getByText('nvidia/nemotron')).toBeInTheDocument()
  expect(screen.getByTitle('contractdigest12345678')).toHaveTextContent('contractdige · baseline digest')
})

test('shows the chosen project directory and keeps runtime fingerprints in collapsed evidence details', async () => {
  vi.mocked(getRun).mockResolvedValue(sampleRun({ project_path: 'evaluation/fixtures/config',
    orchestrator_revision: '1234567890abcdef', orchestrator_digest: 'a'.repeat(64),
    orchestrator_dirty: true, runtime_config_digest: 'b'.repeat(64),
  }))
  renderRun()
  expect(await screen.findByText('evaluation/fixtures/config')).toBeInTheDocument()
  const details = screen.getByText('Runtime fingerprint').closest('details')
  expect(details).not.toHaveAttribute('open')
  expect(details).toHaveTextContent('contains uncommitted changes')
  expect(screen.getByTitle('a'.repeat(64))).toHaveTextContent('aaaaaaaaaaaa')
  expect(screen.getByTitle('b'.repeat(64))).toHaveTextContent('bbbbbbbbbbbb')
  expect(screen.getByTitle('1234567890abcdef')).toHaveTextContent('1234567890ab')
})

test('loads saved terminal event history once and treats EOF as closed, without reconnect warning', async () => {
  vi.mocked(getRun).mockResolvedValue(sampleRun({ status: 'cancelled', failure_reason: 'Cancelled by operator.' }))
  renderRun()
  const stream = await source()
  act(() => { stream.emit('run.status', { message: 'Run cancelled' }); stream.onerror?.() })
  expect(await screen.findByRole('heading', { name: 'Run cancelled.' })).toBeInTheDocument()
  expect(screen.getByText('Run cancelled')).toBeInTheDocument()
  expect(stream.close).toHaveBeenCalledTimes(1)
  expect(screen.queryByText(/Reconnecting automatically/)).not.toBeInTheDocument()
  expect(TestEventSource.instances).toHaveLength(1)
})

test('recovers a lost terminal event from the saved summary and stops reconnecting', async () => {
  let current = sampleRun({ status: 'branching' })
  vi.mocked(getRun).mockImplementation(async () => current)
  renderRun()
  const stream = await source()
  current = sampleRun({ status: 'failed', failure_reason: 'The worker stopped.' })
  act(() => stream.onerror?.())
  expect(await screen.findByRole('heading', { name: 'Run stopped.' })).toBeInTheDocument()
  expect(stream.close).toHaveBeenCalledTimes(1)
  expect(TestEventSource.instances).toHaveLength(1)
  expect(screen.queryByText(/Reconnecting automatically/)).not.toBeInTheDocument()
})

test('offers retry for a failed initial load and opens no stream for a missing run', async () => {
  vi.mocked(getRun).mockRejectedValueOnce(new Error('Run not found')).mockResolvedValue(sampleRun())
  renderRun()
  expect(await screen.findByRole('alert')).toHaveTextContent('Run not found')
  expect(TestEventSource.instances).toHaveLength(0)
  fireEvent.click(screen.getByRole('button', { name: 'Retry loading' }))
  expect(await screen.findByRole('heading', { name: 'Run queued.' })).toBeInTheDocument()
  expect(TestEventSource.instances).toHaveLength(1)
  expect(screen.queryByRole('alert')).not.toBeInTheDocument()
})

test('ignores stale responses and clears event history when navigating between runs', async () => {
  let resolveOld: ((value: RunSummary) => void) | undefined
  vi.mocked(getRun).mockResolvedValueOnce(sampleRun()).mockImplementation((id) => id === 'run-one'
    ? new Promise((resolve) => { resolveOld = resolve })
    : Promise.resolve(sampleRun({ id: 'run-two', status: 'planning' })))
  function Navigation() { const navigate = useNavigate(); return <><button onClick={() => navigate('/runs/run-two')}>Next run</button><RunPage /></> }
  render(<MemoryRouter initialEntries={['/runs/run-one']}><Routes><Route path="/runs/:runId" element={<Navigation />} /></Routes></MemoryRouter>)
  const oldStream = await source()
  act(() => oldStream.emit('run.status', { message: 'Old run evidence' }))
  expect(screen.getByText('Old run evidence')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Next run' }))
  expect(await screen.findByRole('heading', { name: 'Planning three candidates.' })).toBeInTheDocument()
  await act(async () => resolveOld?.(sampleRun({ status: 'failed', failure_reason: 'Old failure' })))
  expect(screen.getByRole('heading', { name: 'Planning three candidates.' })).toBeInTheDocument()
  expect(screen.queryByText('Old run evidence')).not.toBeInTheDocument()
  expect(screen.queryByText('Old failure')).not.toBeInTheDocument()
  expect(oldStream.close).toHaveBeenCalledTimes(1)
  expect(TestEventSource.instances).toHaveLength(2)
})

test('rejects malformed or cross-run events without crashing or polluting evidence', async () => {
  vi.mocked(getRun).mockResolvedValue(sampleRun())
  renderRun()
  const stream = await source()
  act(() => {
    stream.dispatchEvent(new MessageEvent('branch.completed', { data: 'null' }))
    stream.dispatchEvent(new MessageEvent('branch.completed', { data: '{"id":1}' }))
    stream.emit('branch.completed', { run_id: 'unrelated', message: 'Wrong run' })
    stream.emit('branch.completed', { payload: { result: { strategy_id: 'minimal' } } })
  })
  expect(screen.queryByText('Wrong run')).not.toBeInTheDocument()
  expect(screen.queryByRole('table')).not.toBeInTheDocument()
})
