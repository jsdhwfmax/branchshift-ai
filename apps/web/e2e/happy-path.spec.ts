/// <reference types="vite/client" />
import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'
import { readFile } from 'node:fs/promises'
import { createServer, type Server } from 'node:http'
import type { AddressInfo } from 'node:net'
import { extname, resolve, sep } from 'node:path'
import { fileURLToPath } from 'node:url'
import type { RunStatus, RunSummary } from '../src/lib/api'

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
const summary = (status: RunStatus = 'branching'): RunSummary => ({
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

async function mockService(options: { failed?: boolean; unavailable?: boolean; savedLive?: boolean; incomplete?: boolean; behavior?: boolean; liveForm?: boolean } = {}) {
  let current = summary(options.failed ? 'failed' : 'branching')
  if (options.savedLive) {
    current = summary('completed')
    current.mode = 'live'
    current.baseline_commit_sha = 'a'.repeat(40)
    current.baseline_checkpoint_id = 'original-baseline'
    current.baseline_test_contract_digest = 'b'.repeat(64)
    current.baseline_tests_collected = 13
    current.branches = current.branches.map((branch, index) => ({ ...branch, patch, checkpoint_id: `candidate-${index}`, lint_findings: 1, changed_lines: [37,82,55][index] }))
    current.branches[0] = { ...current.branches[0], status: 'failed', tests_collected: 2, tests_passed: 0, tests_failed: 2, test_exit_code: 1, failure_reason: 'Unsupported validator argument.' }
    current.winner_id = 'refactor'
    current.revalidated_checkpoint_id = 'clean-checkpoint'
    current.revalidation = options.incomplete ? null : { ...current.branches[2], checkpoint_id: 'clean-checkpoint', diagnostics: '13 passed, 25 warnings. F401 unused import.' }
  }
  if (options.behavior) {
    const digest = 'c'.repeat(64)
    current.behavior_probes = { cases: [{ id: 'numeric-name', module: 'app.models', model: 'User', payload: { name: 123 } }, { id: 'nullable', module: 'app.models', model: 'User', payload: { name: null } }] }
    current.baseline_probe_results = { suite_digest: digest, observations: [{ id: 'numeric-name', status: 'accepted', value: { name: '123' }, error_type: null, reason: null }, { id: 'nullable', status: 'accepted', value: null, error_type: null, reason: null }] }
    const data = { behavior_probe_results: { suite_digest: digest, observations: [{ id: 'numeric-name', status: 'rejected' as const, value: null, error_type: 'ValidationError', reason: null }, { id: 'nullable', status: 'accepted' as const, value: null, error_type: null, reason: null }] }, behavior_probe_comparison: { suite_digest: digest, review_only: true as const, cases: [{ id: 'numeric-name', status: 'different' as const, basis: 'acceptance' as const }, { id: 'nullable', status: 'match' as const, basis: 'same_observation' as const }] } }
    current.branches[2] = { ...current.branches[2], ...data }
    if (current.revalidation) current.revalidation = { ...current.revalidation, ...data }
  }
  let lastBody: unknown = null
  let posts = 0
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
      return json({ mode: options.liveForm ? 'live' : 'mock', ready: true })
    }
    if (path === '/api/runs' && request.method === 'GET') return json({ runs: options.savedLive ? [{ id: current.id, repo_url: current.repo_url, project_path: current.project_path, mode: current.mode, status: current.status, created_at: current.created_at, updated_at: current.updated_at, winner_id: current.winner_id, baseline_tests_collected: current.baseline_tests_collected }] : [], limit: 5 })
    if (path === '/api/runs' && request.method === 'POST') {
      posts++
      let body = ''
      request.on('data', (part: Buffer) => { body += part.toString('utf8') })
      request.on('end', () => { lastBody = JSON.parse(body); json(current) })
      return
    }
    if (path === '/api/runs/missing') return json({ detail: 'Run not found' }, 404)
    if (path === '/api/runs/browser-fixture') return json(current)
    if (path.endsWith('/patch')) {
      response.writeHead(200, { 'Content-Type': 'text/x-diff', 'Content-Disposition': 'attachment; filename="winner.patch"' })
      return response.end(patch)
    }
    if (path.endsWith('/report')) {
      if (new URL(request.url ?? '/', 'http://127.0.0.1').searchParams.get('format') === 'markdown') {
        response.writeHead(200, { 'Content-Type': 'text/markdown', 'Content-Disposition': 'attachment; filename="evidence.md"' })
        return response.end('# Controlled browser evidence\n13/13 original tests; revalidation retained.\n')
      }
      response.writeHead(200, { 'Content-Type': 'application/json', 'Content-Disposition': 'attachment; filename="evidence.json"' })
      return response.end(JSON.stringify({ run: current }))
    }
    if (path.endsWith('/events')) {
      lastEventId = request.headers['last-event-id'] as string | undefined
      streamRequests++
      response.writeHead(200, { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache' })
      if (options.savedLive) return response.end(sse([...initialEvents, terminalEvent]))
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
    requests: () => ({ posts, lastBody }),
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


test('saved live evidence is discoverable without a new run and puts comparison before proposals', async ({ page }, testInfo) => {
  const service = await mockService({ savedLive: true })
  await page.goto(service.origin)
  await page.getByRole('link', { name: /Saved live run/ }).click()
  await expect(page.getByRole('heading', { name: 'Migration verified.' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'refactor selected.' })).toBeVisible()
  await expect(page.getByText(/55 lines versus 82/)).toBeVisible()
  await expect(page.getByText(/tests passed again/)).toHaveText('13/13 tests passed again')
  expect(service.requests().posts).toBe(0)
  const comparison = await page.getByRole('heading', { name: 'Evidence matrix' }).boundingBox()
  const proposals = await page.getByRole('heading', { name: 'Proposed plans and execution' }).boundingBox()
  expect(comparison!.y).toBeLessThan(proposals!.y)
  await page.getByText('Apply this patch to the recorded commit', { exact: true }).click()
  await expect(page.getByLabel('Patch application commands')).toContainText("--directory='fixtures/pydantic-v1-app' --check")
  await expect(page.getByLabel('Patch application commands')).toContainText('git worktree add --detach')
  const reportDownload = page.waitForEvent('download')
  await page.getByRole('link', { name: 'Readable evidence report' }).click()
  const report = await reportDownload
  expect(await readFile((await report.path())!, 'utf8')).toContain('# Controlled browser evidence')
  await page.getByRole('link', { name: 'Comparison', exact: true }).click()
  await noA11yViolations(page)
  if (testInfo.project.name === 'mobile') await page.setViewportSize({ width: 320, height: 800 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await page.screenshot({ path: testInfo.outputPath('result-first-live-fixture.png'), fullPage: true })
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Migration verified.' })).toBeVisible()
  expect(service.requests().posts).toBe(0)
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.screenshot({ path: testInfo.outputPath('result-first-viewport.png') })
  await page.getByRole('heading', { name: 'Clean baseline revalidation' }).scrollIntoViewIfNeeded()
  await page.screenshot({ path: testInfo.outputPath('revalidation-viewport.png') })
})

test('missing clean result cannot produce a verified label or apply instructions', async ({ page }) => {
  const service = await mockService({ savedLive: true, incomplete: true })
  await page.goto(service.origin + '/runs/browser-fixture')
  await expect(page.getByRole('heading', { name: 'Run complete.' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Review the selected candidate.' })).toBeVisible()
  await expect(page.getByText('verified winner', { exact: true })).toHaveCount(0)
  await expect(page.getByText('Apply this patch to the recorded commit', { exact: true })).toHaveCount(0)
  await expect(page.getByRole('link', { name: 'Download verified patch' })).toHaveCount(0)
  await noA11yViolations(page)
})


test('behavior differences stay visible alongside passing tests and explicit null outputs', async ({ page }, testInfo) => {
  const service = await mockService({ savedLive: true, behavior: true })
  await page.goto(service.origin + '/runs/browser-fixture')
  await expect(page.getByRole('heading', { level: 1, name: 'Review behavior changes.' })).toBeVisible()
  await expect(page.getByText('Original tests verified')).toBeVisible()
  await expect(page.getByRole('link', { name: 'Download selected patch' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Download verified patch' })).toHaveCount(0)
  const review = page.getByRole('region', { name: 'Review behavior changes' })
  await expect(review.getByText('1 match · 1 different · 0 unsupported', { exact: false })).toHaveCount(2)
  await expect(review.getByLabel('Original baseline JSON output').first()).toContainText('"123"')
  await expect(review.getByText('Rejected · ValidationError')).toHaveCount(2)
  await expect(review.getByLabel('Selected candidate JSON output')).toHaveText('null')
  await review.getByText('Supplied input').first().click()
  await expect(review.getByText('"name": 123', { exact: false })).toBeVisible()
  await noA11yViolations(page)
  if (testInfo.project.name === 'mobile') await page.setViewportSize({ width: 320, height: 800 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await review.scrollIntoViewIfNeeded()
  await page.screenshot({ path: testInfo.outputPath('behavior-review.png'), fullPage: true })
  await review.getByRole('heading', { level: 2 }).scrollIntoViewIfNeeded()
  await page.screenshot({ path: testInfo.outputPath('behavior-viewport.png') })
  expect(service.requests().posts).toBe(0)
})

test('advanced validation submits exactly the requested optional inputs', async ({ page }, testInfo) => {
  const service = await mockService({ liveForm: true })
  await page.goto(service.origin)
  await page.getByText('Advanced validation', { exact: false }).click()
  await page.getByLabel('Pinned commit', { exact: false }).fill('short')
  await page.getByRole('button', { name: 'Split run' }).click()
  await expect(page.getByRole('alert')).toContainText('40-character')
  await expect(page.getByLabel('Pinned commit', { exact: false })).toBeFocused()
  expect(service.requests().posts).toBe(0)
  await page.getByLabel('Pinned commit', { exact: false }).fill('a'.repeat(40))
  await expect(page.getByRole('alert')).toHaveCount(0)
  await page.getByLabel('Test extras', { exact: true }).fill('test,dev')
  const behavior_probes = { cases: [{ id: 'numeric', module: 'app.models', model: 'User', payload: { name: 123 } }] }
  await page.getByLabel('Behavior cases JSON', { exact: false }).fill(JSON.stringify(behavior_probes))
  await noA11yViolations(page)
  if (testInfo.project.name === 'mobile') await page.setViewportSize({ width: 320, height: 800 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await page.getByLabel('Behavior cases JSON', { exact: false }).scrollIntoViewIfNeeded()
  await page.screenshot({ path: testInfo.outputPath('advanced-validation.png') })
  if (testInfo.project.name === 'desktop') expect((await page.getByRole('button', { name: 'Split run' }).boundingBox())!.height).toBeLessThan(120)
  await page.getByRole('button', { name: 'Split run' }).click()
  await expect(page.getByRole('heading', { name: 'Replaying sample branches.' })).toBeVisible()
  expect(service.requests()).toEqual({ posts: 1, lastBody: { repo_url: 'https://github.com/jsdhwfmax/branchshift-ai', target: 'pydantic-v2', baseline_ref: 'a'.repeat(40), test_extras: ['test','dev'], behavior_probes } })
})
