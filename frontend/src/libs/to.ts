/**
 * Wraps an async operation in a try-catch block and returns an [error, result] tuple
 * @param promise The Promise to handle
 * @returns A tuple containing error and result [Error | null, T | null]
 */
export async function to<T>(promise: Promise<T>): Promise<[null, T] | [Error, null]> {
  try {
    const result = await promise;
    return [null, result];
  } catch (error) {
    return [error instanceof Error ? error : new Error(String(error)), null];
  }
}

/**
 * Wraps a synchronous operation in a try-catch block and returns an [error, result] tuple
 * @param fn The synchronous function to execute
 * @returns A tuple containing error and result [Error | null, T | null]
 */
export function toSync<T>(fn: () => T): [null, T] | [Error, null] {
  try {
    const result = fn();
    return [null, result];
  } catch (error) {
    return [error instanceof Error ? error : new Error(String(error)), null];
  }
}
