/**
 * Utility functions for logging in a clean format
 */

/**
 * Log a message without the log prefix and file location
 * @param message The message to log
 * @param args Optional arguments to log
 */
export function log(message: string, ...args: any[]): void {
  // Use process.stdout.write instead of log to avoid the prefix and newline
  process.stdout.write(message + "\n");

  // If there are additional arguments, print them on new lines with proper formatting
  if (args.length > 0) {
    for (const arg of args) {
      if (typeof arg === "object") {
        // For objects, format them as JSON with indentation
        process.stdout.write(JSON.stringify(arg, null, 2) + "\n");
      } else {
        // For other types, just convert to string
        process.stdout.write(String(arg) + "\n");
      }
    }
  }
}

/**
 * Log an error message
 * @param message The error message to log
 * @param error Optional error object
 */
export function logError(message: string, error?: any): void {
  process.stderr.write(`ERROR: ${message}\n`);
  if (error) {
    if (error instanceof Error) {
      process.stderr.write(`${error.message}\n`);
    } else if (typeof error === "object") {
      process.stderr.write(JSON.stringify(error, null, 2) + "\n");
    } else {
      process.stderr.write(String(error) + "\n");
    }
  }
}
