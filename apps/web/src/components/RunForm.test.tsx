import { fireEvent, render, screen } from '@testing-library/react'
import { expect, test, vi } from 'vitest'
import RunForm from './RunForm'

test('rejects a non-GitHub repository before submission', async () => {
  const onSubmit = vi.fn()
  render(<RunForm onSubmit={onSubmit} />)
  fireEvent.change(screen.getByLabelText('Public repository'), {
    target: { value: 'https://example.com/owner/repo' },
  })
  fireEvent.click(screen.getByRole('button', { name: /split run/i }))
  expect(await screen.findByRole('alert')).toHaveTextContent('public GitHub')
  expect(onSubmit).not.toHaveBeenCalled()
  expect(screen.getByLabelText('Public repository')).toHaveFocus()
})

test('submits an optional repository-relative Python project directory', async () => {
  const onSubmit = vi.fn().mockResolvedValue(undefined)
  render(<RunForm mode="live" onSubmit={onSubmit} />)
  fireEvent.change(screen.getByLabelText(/Project directory/), { target: { value: '  evaluation/fixtures/config  ' } })
  fireEvent.click(screen.getByRole('button', { name: /split run/i }))
  expect(onSubmit).toHaveBeenCalledWith('https://github.com/jsdhwfmax/branchshift-ai', 'evaluation/fixtures/config')
  expect(screen.getByLabelText(/Project directory/)).toBeDisabled()
})

test('keeps the project location unspecified when the optional field is empty', async () => {
  const onSubmit = vi.fn().mockResolvedValue(undefined)
  render(<RunForm mode="live" onSubmit={onSubmit} />)
  fireEvent.click(screen.getByRole('button', { name: /split run/i }))
  expect(onSubmit).toHaveBeenCalledWith('https://github.com/jsdhwfmax/branchshift-ai', undefined)
})

test.each(['../config', '/evaluation/config'])('rejects non-relative or traversing project directories (%s)', async (path) => {
  const onSubmit = vi.fn()
  render(<RunForm mode="live" onSubmit={onSubmit} />)
  fireEvent.change(screen.getByLabelText(/Project directory/), { target: { value: path } })
  fireEvent.click(screen.getByRole('button', { name: /split run/i }))
  expect(await screen.findByRole('alert')).toHaveTextContent('repository-relative directory')
  expect(screen.getByLabelText(/Project directory/)).toHaveAttribute('aria-invalid', 'true')
  expect(screen.getByLabelText('Public repository')).toHaveAttribute('aria-invalid', 'false')
    expect(onSubmit).not.toHaveBeenCalled()
    expect(screen.getByLabelText(/Project directory/)).toHaveFocus()
})

test('keeps sample replay free of project directory options', () => {
  render(<RunForm mode="mock" onSubmit={vi.fn()} />)
  expect(screen.queryByLabelText(/Project directory/)).not.toBeInTheDocument()
})

test('advanced options are optional and preserve pinned commit, empty extras and typed input', async () => {
  const onSubmit = vi.fn().mockResolvedValue(undefined)
  render(<RunForm mode="live" onSubmit={onSubmit} />)
  fireEvent.click(screen.getByText('Advanced validation'))
  fireEvent.change(screen.getByLabelText(/Pinned commit/), { target: { value: 'A'.repeat(40) } })
  fireEvent.change(screen.getByLabelText('Test extras'), { target: { value: '' } })
  const behavior_probes = { cases: [{ id: 'numeric', module: 'app.models', model: 'User', payload: { name: 123 } }] }
  fireEvent.change(screen.getByLabelText(/Behavior cases JSON/), { target: { value: JSON.stringify(behavior_probes) } })
  fireEvent.click(screen.getByRole('button', { name: /split run/i }))
  expect(onSubmit).toHaveBeenCalledWith('https://github.com/jsdhwfmax/branchshift-ai', undefined, { baseline_ref: 'a'.repeat(40), test_extras: [], behavior_probes })
  expect(screen.getByLabelText(/Pinned commit/)).toBeDisabled()
  expect(screen.getByLabelText(/Behavior cases JSON/)).toBeDisabled()
})

test.each([
  ['Pinned commit', 'abc123', '40-character'],
  ['Test extras', 'test,,dev', 'comma-separated'],
  ['Behavior cases JSON', '{not-json}', 'valid JSON'],
])('invalid %s is focused and prevents submission', async (label, value, message) => {
  const onSubmit = vi.fn()
  render(<RunForm mode="live" onSubmit={onSubmit} />)
  fireEvent.change(screen.getByLabelText(new RegExp(label)), { target: { value } })
  fireEvent.click(screen.getByRole('button', { name: /split run/i }))
  expect(await screen.findByRole('alert')).toHaveTextContent(message)
  expect(screen.getByLabelText(new RegExp(label))).toHaveFocus()
  expect(screen.getByLabelText(new RegExp(label))).toHaveAttribute('aria-invalid', 'true')
  expect(onSubmit).not.toHaveBeenCalled()
})

test('sample replay never offers advanced validation options', () => {
  render(<RunForm mode="mock" onSubmit={vi.fn()} />)
  expect(screen.queryByText('Advanced validation')).not.toBeInTheDocument()
  expect(screen.queryByLabelText(/Behavior cases JSON/)).not.toBeInTheDocument()
})


test('editing an invalid advanced field clears its stale error', async () => {
  render(<RunForm mode="live" onSubmit={vi.fn()} />)
  fireEvent.change(screen.getByLabelText(/Pinned commit/), { target: { value: 'short' } })
  fireEvent.click(screen.getByRole('button', { name: /split run/i }))
  expect(await screen.findByRole('alert')).toHaveTextContent('40-character')
  fireEvent.change(screen.getByLabelText(/Pinned commit/), { target: { value: 'a'.repeat(40) } })
  expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  expect(screen.getByLabelText(/Pinned commit/)).toHaveAttribute('aria-invalid', 'false')
})
