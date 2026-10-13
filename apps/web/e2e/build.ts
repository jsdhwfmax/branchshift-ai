import { execFileSync } from 'node:child_process'
import { createRequire } from 'node:module'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

export default function buildBrowserFixture() {
  const require = createRequire(import.meta.url)
  const cwd = fileURLToPath(new URL('../', import.meta.url))
  const options = { cwd, env: { ...process.env, VITE_API_BASE: '' }, stdio: 'inherit' as const }
  // Execute installed tools only. Test setup must not auto-install dependencies.
  execFileSync(process.execPath, [join(dirname(require.resolve('typescript/package.json')), 'bin/tsc'), '-b'], options)
  execFileSync(process.execPath, [join(dirname(require.resolve('vite/package.json')), 'bin/vite.js'), 'build'], options)
}
