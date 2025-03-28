export function maskDataForLlmApiKey(data: string) {
  // reserve first 8 and last 4 characters
  const length = data.length;
  const mask = '*'.repeat(length - 8 - 4);
  return data.slice(0, 8) + mask + data.slice(-4);
}
