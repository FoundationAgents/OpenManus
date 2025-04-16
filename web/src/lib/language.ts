/**
 * Language
 *
 * @description
 * This file contains the language configuration for the application.
 *
 */

export const LANGUAGE_CODES = {
  en: 'English',
  zh: 'Chinese',
  ko: 'Korean',
  ja: 'Japanese',
};

export const LANGUAGE_CODE_OPTIONS = Object.keys(LANGUAGE_CODES).map(key => ({
  value: key,
  label: LANGUAGE_CODES[key as keyof typeof LANGUAGE_CODES],
}));
