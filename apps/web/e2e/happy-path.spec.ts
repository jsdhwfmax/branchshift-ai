import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'
import { readFile } from 'node:fs/promises'
import { createServer, type Server } from 'node:http'
import type { AddressInfo } from 'node:net'
import { extname, resolve, sep } from 'node:path'
import { fileURLToPath } from 'node:url'

// Every /api response is local test data. Native browser EventSource and downloads
// remain real; no Python API, credentials or model/Sandbox provider is involved.
const servers = new Set<Server>()
test.afterEach(async () => {
  for (const server of servers) {
    server.closeAllConnections()
    await new Promise<void>((resolve) => server.close(() => resolve()))
  }
  servers.clear()
})
const patch = 'diff --git a/src/model.py b/src/model.py\n--- a/src/model.py\n+++ b/src/model.py\n@@ -1 +1 @@\n-old_api()\n+new_api()\n'
const ids = ['minimal', 'compatibility', 'refactor'] as const
const event = (id: number, type: string, extra = {}) => ({
  id, type, run_id: 'browser-fixture', created_at: '2026-09-10T00:00:00Z',
  message: `Recorded browser fixture event ${id}`, branch_id: null, payload: {}, ...extra,
})
const initialEvents = [
  event(1, 'branch.started', { branch_id: 'minimal' }),
  event(2, 'branch.progress', { branch_id: 'minimal', payload: { attempt: 1, max_attempts: 3 } }),
]
const terminalEvent = event(3, 'run.completed')
const summary = (status = 'branching') => ({
  id: 'browser-fixture', repo_url: 'https://github.com/jsdhwfmax/branchshift-ai',
  target: 'pydantic-v2', mode: 'mock', status,
  created_at: '2026-09-10T00:00:00Z', updated_at: '2026-09-10T00:00:00Z',
  strategies: ids.map((id) => ({ id, title: `${id} migration`, rationale: 'A fixed example strategy.',
    ordered_steps: ['Preserve the original behavior.'], source_urls: ['https://docs.pydantic.dev/latest/migration/'],
    target_files: ['src/model.py', 'pyproject.toml'],
  })),
  branches: status === 'completed' ? ids.map((strategy_id, index) => ({
    strategy_id, status: 'passed', tests_collected: 13, tests_passed: 13, tests_failed: 0,
    pip_check_passed: true, lint_findings: index, changed_files: 2, changed_lines: 10 + index,
    elapsed_seconds: 12 + index, patch_applicable: true, pydantic_major: 2,
    test_exit_code: 0, pip_exit_code: 0, test_contract_preserved: true,
  })) : [],
  citations: [{ title: 'Pydantic migration guide', url: 'https://docs.pydantic.dev/latest/migration/',
    evidence: 'Retained documentation is shown with the candidate evidence.' }],
  winner_id: status === 'completed' ? 'minimal' : null,
  patch: status === 'completed' ? patch : null, report: null,
  failure_reason: status === 'failed' ? 'The controlled fixture did not pass verification.' : null,
})
const sse = (events: ReturnType<typeof event>[]) => 'retry: 150\n\n' + events.map((item) =>
  `id: ${item.id}\nevent: ${item.type}\ndata: ${JSON.stringify(item)}\n\n`).join('')

async function mockService(options: { failed?: boolean; unavailable?: boolean } = {}) {
  let current = summary(options.failed ? 'failed' : 'branching')
  let healthRequests = 0
  let streamRequests = 0
  let lastEventId: string | undefined
  let release: () => void = () => {}
  const completed = new Promise<void>((resolve) => { release = resolve })
  // A real same-origin loopback server preserves browser SSE reconnect headers
  // and downloads, which request-interception-only substitutes cannot verify.
  const dist = fileURLToPath(new URL('../dist/', import.meta.url))
  const server = createServer((request, response) => {
    const path = new URL(request.url ?? '/', 'http://127.0.0.1').pathname
    const json = (body: unknown, status = 200) => {
      response.writeHead(status, { 'Content-Type': 'application/json' })
      response.end(JSON.stringify(body))
    }
    if (path === '/api/health/integrations') {
      healthRequests++
      if (options.unavailable && healthRequests === 1) return json({ detail: 'Fixture service unavailable' }, 503)
      return json({ mode: 'mock', ready: true })
    }
    if (path === '/api/runs' && request.method === 'POST') return json(current)
    if (path === '/api/runs/missing') return json({ detail: 'Run not found' }, 404)
    if (path === '/api/runs/browser-fixture') return json(current)
    if (path.endsWith('/patch')) {
      response.writeHead(200, { 'Content-Type': 'text/x-diff', 'Content-Disposition': 'attachment; filename="winner.patch"' })
      return response.end(patch)
    }
    if (path.endsWith('/report')) {
      response.writeHead(200, { 'Content-Type': 'application/json', 'Content-Disposition': 'attachment; filename="evidence.json"' })
      return response.end(JSON.stringify({ run: current }))
    }
    if (path.endsWith('/events')) {
      lastEventId = request.headers['last-event-id'] as string | undefined
      streamRequests++
      response.writeHead(200, { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache' })
      if (current.status === 'failed') return response.end(sse([event(1, 'run.failed')]))
      if (streamRequests === 1) return response.end(sse(initialEvents))
      void completed.then(() => response.end(sse([...initialEvents, terminalEvent])))
      return
    }
    if (path.startsWith('/api/')) return json({ detail: 'Unknown test route' }, 404)
    const file = resolve(dist, path.startsWith('/assets/') ? `.${path}` : 'index.html')
    if (!file.startsWith(resolve(dist) + sep)) return json({ detail: 'Unknown asset' }, 404)
    const mime: Record<string, string> = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.woff': 'font/woff', '.woff2': 'font/woff2' }
    void readFile(file).then((body) => {
      response.writeHead(200, { 'Content-Type': mime[extname(file)] ?? 'application/octet-stream' })
      response.end(body)
    }).catch(() => json({ detail: 'Unknown asset' }, 404))
  })
  servers.add(server)
  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve))
  return {
    origin: `http://127.0.0.1:${(server.address() as AddressInfo).port}`,
    finish() { current = summary('completed'); release() },
    connection: () => ({ streamRequests, lastEventId }),
  }
}

async function noA11yViolations(page: Page) {
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
  expect(results.violations.map(({ id, impact, nodes }) => ({ id, impact, targets: nodes.map((node) => node.target) }))).toEqual([])
}

test('keyboard happy path reconnects native SSE, downloads exact evidence and survives refresh', async ({ page }, testInfo) => {
  const service = await mockService()
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.goto(service.origin)
  await page.keyboard.press('Tab')
  await expect(page.getByRole('link', { name: 'Skip to content' })).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('heading', { level: 1 })).toBeFocused()
  await expect(page.getByRole('button', { name: 'Replay sample' })).toBeEnabled()
  await noA11yViolations(page)
  await page.screenshot({ path: testInfo.outputPath('preflight.png'), fullPage: true })
  await page.keyboard.press('Tab')
  await expect(page.getByLabel('Public repository')).toBeFocused()
  await page.keyboard.press('Tab')
  await expect(page.getByRole('button', { name: 'Replay sample' })).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('heading', { name: 'Replaying sample branches.' })).toBeFocused()
  await expect(page.getByText('Proposal attempts started: 1 (limit 3)')).toBeVisible()
  await expect(page.getByText('No winning patch is available for this run.')).toHaveCount(0)
  await expect.poll(() => service.connection().streamRequests).toBe(2)
  expect(service.connection().lastEventId).toBe('2')
  const animation = await page.locator('.state-running .lane-rail span').evaluate((element) => getComputedStyle(element).animationDuration)
  expect(parseFloat(animation)).toBeLessThanOrEqual(0.00001)
  service.finish()
  await expect(page.getByRole('heading', { name: 'Sample replay complete.' })).toBeVisible()
  await expect(page.getByRole('list', { name: 'Recent run events' }).getByText('Recorded browser fixture event 2')).toHaveCount(1)
  await expect(page.getByText('verified winner', { exact: true })).toHaveCount(0)
  await page.getByText('Planned target files', { exact: true }).first().click()
  await expect(page.getByText('src/model.py', { exact: true }).first()).toBeVisible()
  await noA11yViolations(page)
  await page.screenshot({ path: testInfo.outputPath('completed.png'), fullPage: true })

  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('link', { name: 'download ↓', exact: true }).click()
  const download = await downloadPromise
  expect(await readFile((await download.path())!, 'utf8')).toBe(patch)
  const evidencePromise = page.waitForEvent('download')
  await page.getByRole('link', { name: /Download sample evidence/ }).click()
  const evidence = await evidencePromise
  expect(JSON.parse(await readFile((await evidence.path())!, 'utf8')).run.patch).toBe(patch)

  await page.reload()
  await expect(page.getByRole('heading', { name: 'Sample replay complete.' })).toBeVisible()
  await expect(page.getByLabel('Sample patch contents')).toContainText('new_api()')
  await expect(page.getByText(/Reconnecting automatically/)).toHaveCount(0)
  if (testInfo.project.name === 'mobile') await page.setViewportSize({ width: 320, height: 800 })
  await noA11yViolations(page)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  const table = page.getByRole('region', { name: 'Branch evidence comparison' })
  await table.focus()
  await expect(table).toBeFocused()
  if (await table.evaluate((element) => element.scrollWidth > element.clientWidth)) {
    await page.keyboard.press('ArrowRight')
    await expect.poll(() => table.evaluate((element) => element.scrollLeft)).toBeGreaterThan(0)
  }
  expect(errors).toEqual([])
})

test('validation, service retry and saved failure remain useful without a false winner', async ({ page }) => {
  const service = await mockService({ failed: true, unavailable: true })
  await page.goto(service.origin)
  await expect(page.getByRole('alert')).toContainText('Fixture service unavailable')
  await expect(page.getByRole('button', { name: 'Split run' })).toBeDisabled()
  await page.getByRole('button', { name: 'Retry connection' }).click()
  await expect(page.getByRole('button', { name: 'Replay sample' })).toBeEnabled()
  await page.getByLabel('Public repository').fill('https://example.com/private/repo')
  await page.getByRole('button', { name: 'Replay sample' }).click()
  await expect(page.getByRole('alert')).toContainText('public GitHub')
  await expect(page.getByLabel('Public repository')).toBeFocused()
  await noA11yViolations(page)
  await page.getByLabel('Public repository').fill('https://github.com/jsdhwfmax/branchshift-ai')
  await page.keyboard.press('Enter')
  await expect(page.getByRole('heading', { name: 'Run stopped.' })).toBeVisible()
  await expect(page.getByRole('alert')).toContainText('did not pass verification')
  await expect(page.getByText('No winning patch is available for this run.')).toBeVisible()
  await expect(page.getByText('verified winner', { exact: true })).toHaveCount(0)
  await expect(page.getByRole('link', { name: 'download ↓', exact: true })).toHaveCount(0)
  await noA11yViolations(page)
  await page.goto(service.origin + '/runs/missing')
  await expect(page.getByRole('alert')).toHaveText('Run not found')
  await expect(page.getByRole('button', { name: 'Retry loading' })).toBeVisible()
  await noA11yViolations(page)
  await page.getByRole('link', { name: 'Return to preflight' }).click()
  await expect(page.getByRole('button', { name: 'Replay sample' })).toBeEnabled()
})
