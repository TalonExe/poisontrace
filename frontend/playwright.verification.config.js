import mocked from './playwright.config.js';
import connected from './playwright.mcp.config.js';
import production from './playwright.production.config.js';

const family = process.env.POISONTRACE_VERIFY_FAMILY;
const selected = { mocked, connected, production }[family];
if (!selected || !process.env.POISONTRACE_VERIFY_ARTIFACT)
  throw new Error('Use scripts/verify.py to own verification servers and artifacts');

export default {
  ...selected,
  webServer: undefined,
  globalTeardown: undefined,
  workers: family === 'mocked' ? 2 : 1,
  retries: 0,
  reporter: [['list'], ['json', { outputFile: `${process.env.POISONTRACE_VERIFY_ARTIFACT}/playwright.json` }]],
  outputDir: `${process.env.POISONTRACE_VERIFY_ARTIFACT}/test-results`,
  use: { ...selected.use, trace: 'retain-on-failure', screenshot: 'only-on-failure' },
};
