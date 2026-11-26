export const executionModels = Object.freeze({
  scripted: "scripted-soc-v2",
  gemini: "gemini-3.5-flash-lite",
  openai: "gpt-5-mini",
});
export const EXECUTION_STORAGE_KEY = "poisontrace.synthetic.execution";

export function resolveExecution(
  selection,
  configurations,
  credentials,
  required,
) {
  const configuration = configurations.find(
    (c) => `config:${c.id}` === selection,
  );
  const provider =
    required?.provider ||
    (selection === "scripted" ? "scripted" : configuration?.model);
  const model = required?.model || executionModels[provider];
  if (provider === "scripted")
    return {
      provider,
      model,
      credentialId: undefined,
      configuration: undefined,
      valid: true,
    };
  const credential = credentials.find(
    (c) =>
      c.credential_id === configuration?.credentialId &&
      c.provider === provider,
  );
  const valid =
    ["gemini", "openai"].includes(provider) &&
    configuration?.model === provider &&
    Boolean(credential);
  return {
    provider,
    model,
    configuration,
    credentialId: valid ? credential.credential_id : undefined,
    valid,
  };
}
