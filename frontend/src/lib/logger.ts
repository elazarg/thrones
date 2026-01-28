/**
 * Simple logging utility that can be disabled in production.
 *
 * In development, logs to console with prefixes.
 * In production, logs are disabled (except errors).
 */

const isDev = import.meta.env.DEV;

export const logger = {
  debug: (message: string, ...args: unknown[]) => {
    if (isDev) {
      console.debug(`[DEBUG] ${message}`, ...args);
    }
  },

  info: (message: string, ...args: unknown[]) => {
    if (isDev) {
      console.info(`[INFO] ${message}`, ...args);
    }
  },

  warn: (message: string, ...args: unknown[]) => {
    if (isDev) {
      console.warn(`[WARN] ${message}`, ...args);
    }
  },

  error: (message: string, ...args: unknown[]) => {
    // Always log errors, even in production
    console.error(`[ERROR] ${message}`, ...args);
  },
};
