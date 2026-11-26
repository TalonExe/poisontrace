import { test as base, expect } from '@playwright/test';
import { createHash } from 'node:crypto';
import path from 'node:path';

export { expect };
export const test = base.extend({
  page: async ({ page }, use) => {
    const directory = process.env.POISONTRACE_VERIFY_ARTIFACT;
    if (directory) {
      const screenshot = page.screenshot.bind(page);
      page.screenshot = (options = {}) => {
        if (!options.path) return screenshot(options);
        const id = createHash('sha256').update(String(options.path)).digest('hex').slice(0, 12);
        return screenshot({ ...options, path: path.join(directory, 'captures', `${id}-${path.basename(options.path)}`) });
      };
    }
    await use(page);
  },
});
