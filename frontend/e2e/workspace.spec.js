import { test, expect } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.clear())
  await page.goto('/')
})

async function signIn(page) {
  await page.getByLabel('Analyst ID').fill('analyst')
  await page.getByLabel('Local passcode').fill('synthetic-only')
  await page.getByRole('button', { name: /Open dashboard/ }).click()
  await expect(page.getByRole('heading', { name: 'Choose a session.' })).toBeVisible()
}

test('login accepts the synthetic demo account', async ({ page }) => {
  await signIn(page)
  await expect(page.getByText('Authentication alert study')).toBeVisible()
})

test('session workspace creates a session and selects a provider', async ({ page }) => {
  await signIn(page)
  await page.getByRole('button', { name: /New session/ }).click()
  await page.getByLabel('Session name').fill('OpenAI browser study')
  await page.getByRole('button', { name: /OpenAI API LLM/ }).click()
  await expect(page.getByRole('button', { name: /OpenAI API LLM/ })).toHaveClass(/active/)
  await page.getByRole('button', { name: /Save session/ }).click()
  await expect(page.getByText('OpenAI browser study')).toBeVisible()
})

test('sidebar navigates to scenarios and back to sessions', async ({ page }) => {
  await signIn(page)
  await page.getByRole('button', { name: 'Open navigation' }).click()
  await page.getByRole('button', { name: /Scenarios/ }).click()
  await expect(page.getByRole('heading', { name: 'Manage scenarios.' })).toBeVisible()
  await page.getByRole('button', { name: 'Return to sessions' }).click()
  await expect(page.getByRole('heading', { name: 'Choose a session.' })).toBeVisible()
})

test('credential selector displays masked references without plaintext secrets', async ({ page }) => {
  await page.route('**/api/credentials', async route => route.fulfill({ json: [{ credential_id: 'cred-1', provider: 'gemini', label: 'Research', masked: '••••1234' }] }))
  await signIn(page)
  await page.getByRole('button', { name: /Edit/ }).first().click()
  await expect(page.getByText('Research · ••••1234')).toBeVisible()
  const credentialSelect = page.locator('select').filter({ hasText: 'Research' })
  await credentialSelect.selectOption('cred-1')
  await expect(credentialSelect).toHaveValue('cred-1')
  await expect(page.locator('body')).not.toContainText('synthetic-only')
})
