export function maskDataForLlmApiKey(data: string) {
  // reserve first 8 and last 4 characters
  const length = data.length;
  const mask = '*'.repeat(length - 8 - 4);
  return data.slice(0, 8) + mask + data.slice(-4);
}

export function isMaybeSameMaskedLlmApiKey(original: string, masked: string) {
  return masked.slice(0, 8) === original.slice(0, 8) && masked.slice(-4) === original.slice(-4);
}

export function maskDataForFlatObject(env: Record<string, string>) {
  return Object.fromEntries(Object.entries(env).map(([key]) => [key, '*********']));
}
