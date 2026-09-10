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
})

test('keeps sample replay free of project directory options', () => {
  render(<RunForm mode="mock" onSubmit={vi.fn()} />)
  expect(screen.queryByLabelText(/Project directory/)).not.toBeInTheDocument()
})
