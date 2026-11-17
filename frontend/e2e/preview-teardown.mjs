// Stop only a test preview that acknowledges the test-only shutdown endpoint.
export default async function teardown() {
  try {
    const response = await fetch("http://127.0.0.1:4173/__test_shutdown", {method:"POST"});
    if (!response.ok) return;
    for (let attempt=0; attempt<50; attempt++) {
      await new Promise(resolve=>setTimeout(resolve,100));
      try { await fetch("http://127.0.0.1:4173/", {signal:AbortSignal.timeout(500)}); }
      catch { return; }
    }
  } catch { /* The test preview has already exited. */ }
}
