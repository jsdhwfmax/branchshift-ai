import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { expect, test } from 'vitest'
import HomePage from './HomePage'

test('states the deterministic decision contract', () => {
  render(<MemoryRouter><HomePage /></MemoryRouter>)
  expect(screen.getByRole('heading', { name: /One baseline/i })).toBeInTheDocument()
  expect(screen.getByText(/tests—not taste—select the patch/i)).toBeInTheDocument()
  expect(screen.getByText('Compatibility')).toBeInTheDocument()
})
