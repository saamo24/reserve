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
  timezone: string;
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
  notes?: string | null;
}

export interface BranchCreate {
  name: string;
  address: string;
  timezone?: string;
  opening_time: string;
  closing_time: string;
  slot_duration_minutes?: number;
  is_active?: boolean;
}

export interface BranchUpdate {
  name?: string;
  address?: string;
  timezone?: string;
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

export interface Layout {
  width: number;
  height: number;
  tables: LayoutTable[];
}

export type TableStatus = 'available' | 'reserved' | 'disabled';
