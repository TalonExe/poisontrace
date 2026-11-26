import https from 'node:https';
import http from 'node:http';

export default async function teardown() {
  const hosted = process.env.POISONTRACE_TEST_CONTENT_PROFILE === 'hosted';
  const origin = `${hosted ? 'https' : 'http'}://127.0.0.1:4176`;
  await new Promise((resolve, reject) => {
    const request = (hosted ? https : http).request(`${origin}/__test_shutdown`, {
      method:'POST', headers:{Origin:origin}, rejectUnauthorized:false, timeout:5000,
    }, response => { response.resume(); response.on('end', resolve); });
    request.on('error', reject);
    request.on('timeout', () => request.destroy(new Error('Synthetic shutdown timed out')));
    request.end();
  });
}
