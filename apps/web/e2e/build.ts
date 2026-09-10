import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

export default function buildBrowserFixture() {
  execFileSync('pnpm', ['build'], {
    cwd: fileURLToPath(new URL('../', import.meta.url)),
    env: { ...process.env, VITE_API_BASE: '' },
    stdio: 'inherit',
  })
}
