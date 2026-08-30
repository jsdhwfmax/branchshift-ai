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
