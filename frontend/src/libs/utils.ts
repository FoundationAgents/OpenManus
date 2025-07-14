import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatNumber(
  num: number,
  config: {
    autoUnit?: boolean;
    uppercase?: boolean;
  } = {},
) {
  const { autoUnit = false, uppercase = false } = config;

  if (autoUnit) {
    const baseUnits = ['', 'k', 'm', 'b', 't'];
    const units = uppercase ? baseUnits.map(u => u.toUpperCase()) : baseUnits;
    const order = Math.floor(Math.log10(Math.abs(num)) / 3);
    const unitName = units[order] || '';

    if (order > 0) {
      const scaled = num / Math.pow(1000, order);
      return (
        scaled.toLocaleString('en-US', {
          minimumFractionDigits: 0,
          maximumFractionDigits: 1,
        }) + unitName
      );
    }
  }

  return num.toLocaleString('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
}
