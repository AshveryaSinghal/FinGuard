export function tierClass(level?: string | null): string {
  return String(level || 'unassessed').trim().toLowerCase().replace(/\s+/g, '-');
}
