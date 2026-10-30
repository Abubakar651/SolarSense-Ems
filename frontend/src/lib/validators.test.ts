import { describe, expect, it } from 'vitest';
import { passwordStrength, rules, validateValue } from './validators';

const ctx = (label = 'Email address', others: Record<string, string> = {}) => ({
  label,
  valueOf: (id: string) => others[id] ?? '',
});

describe('validateValue', () => {
  it('asks for a missing required value using the lower-cased label', () => {
    expect(validateValue('  ', [rules.required()], ctx())).toBe('Enter your email address.');
  });

  it('accepts a filled required value', () => {
    expect(validateValue('a', [rules.required()], ctx())).toBe('');
  });

  it('asks an unchecked box to be accepted', () => {
    expect(validateValue(false, [rules.checked()], ctx('Terms'))).toBe(
      'You need to accept to continue.',
    );
    expect(validateValue(true, [rules.checked()], ctx('Terms'))).toBe('');
  });

  it('rejects an invalid email and accepts a valid one', () => {
    expect(validateValue('no-at-sign', [rules.email()], ctx())).toBe(
      'Enter a valid email address, like name@example.com.',
    );
    expect(validateValue('a@b.co', [rules.email()], ctx())).toBe('');
  });

  it('reports the length shortfall for min', () => {
    expect(validateValue('abc', [rules.min(8)], ctx('Password'))).toBe(
      'Use at least 8 characters (you have 3).',
    );
    expect(validateValue('abcdefgh', [rules.min(8)], ctx('Password'))).toBe('');
  });

  it('checks that two fields match', () => {
    const others = { pw: 'secret123' };
    expect(validateValue('other', [rules.match('pw')], ctx('Confirm', others))).toBe(
      "The two passwords don't match. Re-enter them.",
    );
    expect(validateValue('secret123', [rules.match('pw')], ctx('Confirm', others))).toBe('');
  });

  it('bounds numbers inclusively and rejects non-numbers', () => {
    const r = [rules.num(1, 10)];
    expect(validateValue('0', r, ctx('Size'))).toBe('Enter a number between 1 and 10.');
    expect(validateValue('1', r, ctx('Size'))).toBe('');
    expect(validateValue('10', r, ctx('Size'))).toBe('');
    expect(validateValue('11', r, ctx('Size'))).toBe('Enter a number between 1 and 10.');
    expect(validateValue('abc', r, ctx('Size'))).toBe('Enter a number between 1 and 10.');
  });

  it('skips non-required rules for an empty value', () => {
    expect(validateValue('', [rules.email(), rules.min(8)], ctx())).toBe('');
  });

  it('returns the first failing rule only', () => {
    expect(validateValue('', [rules.required(), rules.email()], ctx())).toBe(
      'Enter your email address.',
    );
  });
});

describe('passwordStrength', () => {
  it('scores an empty password as 0', () => {
    expect(passwordStrength('')).toBe(0);
  });

  it('adds one point per satisfied criterion', () => {
    expect(passwordStrength('abcdefgh')).toBe(1);
    expect(passwordStrength('Abcdefgh')).toBe(2);
    expect(passwordStrength('Abcdefg1')).toBe(3);
    expect(passwordStrength('Abcdef1!')).toBe(4);
  });

  it('counts a 14-character password as long enough for the last point', () => {
    expect(passwordStrength('abcdefghijklmn')).toBe(2);
  });
});
