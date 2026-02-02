import { describe, it, expect } from 'vitest';
import { toFraction } from './mathUtils';

describe('toFraction', () => {
  it('returns "0" for zero', () => {
    expect(toFraction(0)).toBe('0');
  });

  it('returns "1" for one', () => {
    expect(toFraction(1)).toBe('1');
  });

  it('converts 0.5 to "1/2"', () => {
    expect(toFraction(0.5)).toBe('1/2');
  });

  it('converts 0.333... to "1/3"', () => {
    expect(toFraction(1 / 3)).toBe('1/3');
  });

  it('converts 0.666... to "2/3"', () => {
    expect(toFraction(2 / 3)).toBe('2/3');
  });

  it('converts 0.25 to "1/4"', () => {
    expect(toFraction(0.25)).toBe('1/4');
  });

  it('converts 0.75 to "3/4"', () => {
    expect(toFraction(0.75)).toBe('3/4');
  });

  it('converts 0.2 to "1/5"', () => {
    expect(toFraction(0.2)).toBe('1/5');
  });

  it('simplifies fractions (e.g., 2/4 becomes 1/2)', () => {
    expect(toFraction(0.5)).toBe('1/2');
  });

  it('falls back to decimal for non-standard fractions', () => {
    expect(toFraction(0.42)).toBe('0.42');
  });

  it('handles 1/6', () => {
    expect(toFraction(1 / 6)).toBe('1/6');
  });

  it('handles 5/6', () => {
    expect(toFraction(5 / 6)).toBe('5/6');
  });
});
