import type { BranchResponse, LayoutDocument, LayoutV2, LayoutZone, LayoutFloor } from './types';
import { isLayoutV1, isLayoutV2 } from './types';

/** Merge class names. */
export function cn(...inputs: (string | undefined | null | false)[]): string {
  return inputs.filter(Boolean).join(' ');
}

/** Format date as e.g. "Friday, Feb 20, 2025". */
export function formatDateDisplay(dateStr: string): string {
  const d = new Date(dateStr + 'T12:00:00');
  return d.toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

/** Format time string (HH:MM or HH:MM:SS) for display. */
export function formatTime(timeStr: string): string {
  const parts = timeStr.split(':');
  const hours = parseInt(parts[0], 10);
  const minutes = parts[1] || '00';
  const ampm = hours >= 12 ? 'PM' : 'AM';
  const h = hours % 12 || 12;
  return `${h}:${minutes} ${ampm}`;
}

/** Today in YYYY-MM-DD (local). */
export function getTodayDate(): string {
  const d = new Date();
  return d.toISOString().slice(0, 10);
}

/** Format Date or date string for API: YYYY-MM-DD. */
export function formatDate(d: Date | string): string {
  if (typeof d === 'string') {
    const parsed = new Date(d + (d.includes('T') ? '' : 'T12:00:00'));
    return isNaN(parsed.getTime()) ? d : parsed.toISOString().slice(0, 10);
  }
  return d.toISOString().slice(0, 10);
}

/** Whether the date is in the past (before today). */
export function isPastDate(dateStr: string): boolean {
  const today = getTodayDate();
  return dateStr < today;
}

/** Create URL-friendly slug from string. */
export function slugify(text: string): string {
  return text
    .toLowerCase()
    .trim()
    .replace(/[^\w\s-]/g, '')
    .replace(/[\s_-]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

/** Build a map of slug -> branch for lookup. */
export function createSlugToBranchMap(branches: BranchResponse[]): Map<string, BranchResponse> {
  const map = new Map<string, BranchResponse>();
  for (const b of branches) {
    map.set(slugify(b.name), b);
  }
  return map;
}

/** Get branch id from slug using slug map (slug is typically from branch name). */
export function getBranchIdFromSlug(
  slug: string,
  slugMap: Map<string, BranchResponse>
): string | null {
  const branch = slugMap.get(slug);
  return branch ? branch.id : null;
}

/** Normalize layout (v1 or v2) to v2 format for UI consistency. */
export function normalizeLayoutToV2(layout: LayoutDocument): LayoutV2 {
  if (isLayoutV2(layout)) {
    return layout;
  }
  
  // Convert v1 to v2: create a single "Indoor" zone with one floor
  const defaultZone: LayoutZone = {
    id: 'default-indoor-zone',
    name: 'Indoor',
    type: 'indoor',
    floors: [
      {
        id: 'default-floor-1',
        name: 'Floor 1',
        width: layout.width,
        height: layout.height,
        tables: layout.tables,
      },
    ],
  };
  
  return {
    zones: [defaultZone],
  };
}
