export function maskDataForLlmApiKey(data: string) {
  const length = data.length;
  const mask = '*'.repeat(length - 4);
  return data.slice(0, 4) + mask + data.slice(-4);
}

export function isMaybeSameMaskedLlmApiKey(original: string, masked: string) {
  const maskedOriginal = maskDataForLlmApiKey(original);
  return masked === maskedOriginal;
}

export function maskDataForFlatObject(env: Record<string, string>) {
  return Object.fromEntries(Object.entries(env).map(([key]) => [key, '*********']));
}
