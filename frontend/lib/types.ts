/** API types matching backend schemas. */

export const ReservationStatus = {
  PENDING: 'PENDING',
  CONFIRMED: 'CONFIRMED',
  CANCELLED: 'CANCELLED',
  COMPLETED: 'COMPLETED',
} as const;
export type ReservationStatus = (typeof ReservationStatus)[keyof typeof ReservationStatus];

export const TableLocation = {
  INDOOR: 'INDOOR',
  OUTDOOR: 'OUTDOOR',
  VIP: 'VIP',
} as const;
export type TableLocation = (typeof TableLocation)[keyof typeof TableLocation];

export interface BranchResponse {
  id: string;
  name: string;
  address: string;
  opening_time: string;
  closing_time: string;
  slot_duration_minutes: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TableResponse {
  id: string;
  branch_id: string;
  table_number: string;
  capacity: number;
  location: TableLocation;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface GuestMeResponse {
  telegram_linked: boolean;
  tg_bot_username: string | null;
}

export interface ReservationResponse {
  id: string;
  branch_id: string;
  table_id: string;
  full_name: string;
  phone_number: string;
  email: string | null;
  reservation_date: string;
  start_time: string;
  end_time: string;
  status: ReservationStatus;
  notes: string | null;
  reservation_code?: string | null;
  /** Base64-encoded PNG QR code for this reservation */
  qr_code?: string | null;
  created_at: string;
  updated_at: string;
}

export interface Slot {
  start_time: string;
  end_time: string;
}

export interface ReservationCreate {
  branch_id: string;
  reservation_date: string;
  start_time: string;
  table_id?: string;
  full_name: string;
  phone_number: string;
  email?: string | null;
  number_of_guests: number;
  notes?: string | null;
}

export interface BranchCreate {
  name: string;
  address: string;
  opening_time: string;
  closing_time: string;
  slot_duration_minutes?: number;
  is_active?: boolean;
}

export interface BranchUpdate {
  name?: string;
  address?: string;
  opening_time?: string;
  closing_time?: string;
  slot_duration_minutes?: number;
  is_active?: boolean;
}

export interface TableCreate {
  branch_id: string;
  table_number: string;
  capacity: number;
  location?: TableLocation;
  is_active?: boolean;
}

export interface TableUpdate {
  table_number?: string;
  capacity?: number;
  location?: TableLocation;
  is_active?: boolean;
}

export interface ReservationUpdate {
  status?: ReservationStatus;
  notes?: string | null;
}

export interface PaginationMeta {
  total: number;
  page: number;
  page_size: number;
}

export interface PaginatedResponse<T> {
  data: T[];
  meta: PaginationMeta;
}

export interface DashboardStats {
  total_reservations: number;
  active_reservations: number;
  upcoming_reservations: number;
  occupancy_rate_percent: number;
}

// Floor plan layout (matches backend layout JSON)
export type LayoutTableShape = 'round' | 'rect';
export type ZoneType = 'indoor' | 'outdoor';

export interface LayoutTable {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  rotation: number;
  shape: LayoutTableShape;
  capacity: number;
  table_number: string;
}

// Layout V1 (legacy: single canvas)
export interface LayoutV1 {
  width: number;
  height: number;
  tables: LayoutTable[];
}

// Layout V2 (zones/floors)
export interface LayoutFloor {
  id: string;
  name: string;
  width: number;
  height: number;
  tables: LayoutTable[];
}

export interface LayoutZone {
  id: string;
  name: string;
  type: ZoneType;
  // Indoor: floors required
  floors?: LayoutFloor[];
  // Outdoor: width/height/tables required
  width?: number;
  height?: number;
  tables?: LayoutTable[];
}

export interface LayoutV2 {
  zones: LayoutZone[];
}

// Union type for layout documents
export type LayoutDocument = LayoutV1 | LayoutV2;

// Type guard helpers
export function isLayoutV1(layout: LayoutDocument): layout is LayoutV1 {
  return 'width' in layout && 'height' in layout && 'tables' in layout && !('zones' in layout);
}

export function isLayoutV2(layout: LayoutDocument): layout is LayoutV2 {
  return 'zones' in layout;
}

// Helper to check if layout has any tables
export function layoutHasTables(layout: LayoutDocument): boolean {
  if (isLayoutV1(layout)) {
    return layout.tables.length > 0;
  }
  // V2: check all zones
  for (const zone of layout.zones) {
    if (zone.type === 'outdoor' && zone.tables && zone.tables.length > 0) {
      return true;
    }
    if (zone.type === 'indoor' && zone.floors) {
      for (const floor of zone.floors) {
        if (floor.tables.length > 0) {
          return true;
        }
      }
    }
  }
  return false;
}

// Backward compatibility alias
export type Layout = LayoutV1;

export type TableStatus = 'available' | 'reserved' | 'disabled';
