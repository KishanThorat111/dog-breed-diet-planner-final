import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatWeight(kg: number | null | undefined): string {
  if (kg == null) return "Unknown";
  return `${kg} kg (${(kg * 2.205).toFixed(1)} lbs)`;
}

export function formatAge(months: number | null | undefined): string {
  if (months == null) return "Unknown";
  if (months < 12) return `${months} month${months !== 1 ? "s" : ""}`;
  const years = Math.floor(months / 12);
  const rem = months % 12;
  return rem > 0 ? `${years}y ${rem}mo` : `${years} year${years !== 1 ? "s" : ""}`;
}

export function formatCalories(kcal: number): string {
  return `${Math.round(kcal).toLocaleString()} kcal`;
}

export function capitalize(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1).replace(/_/g, " ");
}
