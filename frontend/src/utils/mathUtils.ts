/**
 * Shared math utility functions.
 */

/**
 * Convert a decimal probability to a simple fraction string.
 * Handles common fractions like 1/2, 1/3, 1/4, etc.
 *
 * @param decimal - A number between 0 and 1
 * @returns A string representation as a fraction (e.g., "1/3") or decimal (e.g., "0.42")
 */
export function toFraction(decimal: number): string {
  if (decimal === 0) return '0';
  if (decimal === 1) return '1';

  // Common denominators to try
  const denominators = [2, 3, 4, 5, 6, 8, 10, 12];

  for (const d of denominators) {
    const n = Math.round(decimal * d);
    if (Math.abs(n / d - decimal) < 0.0001) {
      // Simplify the fraction using GCD
      const gcd = (a: number, b: number): number => (b === 0 ? a : gcd(b, a % b));
      const g = gcd(n, d);
      const num = n / g;
      const den = d / g;
      if (den === 1) return `${num}`;
      return `${num}/${den}`;
    }
  }

  // Fall back to decimal with 2 places
  return decimal.toFixed(2);
}
