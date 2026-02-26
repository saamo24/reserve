import axios, { type AxiosError } from 'axios';
import type {
  BranchResponse,
  BranchCreate,
  BranchUpdate,
  TableResponse,
  TableCreate,
  TableUpdate,
  GuestMeResponse,
  ReservationResponse,
  ReservationCreate,
  ReservationUpdate,
  PaginatedResponse,
  DashboardStats,
  Layout,
  LayoutDocument,
} from './types';
import type { Slot } from './types';

const getBaseUrl = (): string => {
  if (typeof process !== 'undefined' && process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  return 'http://localhost:8000';
};

const getAuthToken = (): string | null => {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('access_token');
};

const getGuestToken = (): string | null => {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('guest_token');
};

const setGuestToken = (token: string): void => {
  if (typeof window === 'undefined') return;
  localStorage.setItem('guest_token', token);
};

/**
 * Single API client for all backend requests. withCredentials must stay true
 * so the guest_id cookie is sent and the same guest session is used (required for
 * My Reservations and reservation creation to match).
 * Also supports guest token in Authorization header as fallback for Safari ITP.
 */
const api = axios.create({
  baseURL: getBaseUrl(),
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
});

api.interceptors.request.use((config: import('axios').InternalAxiosRequestConfig) => {
  // Ensure credentials are always sent; prevent per-request overrides from breaking guest session
  config.withCredentials = true;
  
  // Add admin auth token if available
  const authToken = getAuthToken();
  if (authToken) {
    config.headers.Authorization = `Bearer ${authToken}`;
  } else {
    // Fallback: Use guest token if cookies aren't working (Safari ITP)
    // Only use guest token if no admin token is present
    const guestToken = getGuestToken();
    if (guestToken) {
      config.headers.Authorization = `Bearer ${guestToken}`;
    }
  }
  
  return config;
});

api.interceptors.response.use(
  (r: import('axios').AxiosResponse) => {
    // Store guest token from response header (Safari ITP fallback)
    // Backend sends this in X-Guest-Token header on every response
    const guestToken = r.headers['x-guest-token'];
    if (guestToken && typeof guestToken === 'string') {
      setGuestToken(guestToken);
    }
    return r;
  },
  (err: AxiosError<{ detail?: string | unknown }>) => {
    const detail = err.response?.data?.detail;
    const message = typeof detail === 'string' ? detail : JSON.stringify(detail ?? err.message);
    const e = new Error(message) as Error & { status?: number };
    e.status = err.response?.status;
    return Promise.reject(e);
  }
);

// —— Public (no auth) ——

export async function getBranches(): Promise<BranchResponse[]> {
  const { data } = await api.get<BranchResponse[]>('/branches');
  return data;
}

export async function getBranch(branchId: string): Promise<BranchResponse> {
  const { data } = await api.get<BranchResponse>(`/branches/${branchId}`);
  return data;
}

export async function getSlots(branchId: string, date: string): Promise<Slot[]> {
  const { data } = await api.get<Slot[]>(`/branches/${branchId}/slots`, {
    params: { date },
  });
  return data;
}

export async function getBranchTables(branchId: string): Promise<TableResponse[]> {
  const { data } = await api.get<TableResponse[]>(`/branches/${branchId}/tables`);
  return data;
}

export async function getLayoutPublic(branchId: string): Promise<LayoutDocument> {
  const { data } = await api.get<LayoutDocument>(`/branches/${branchId}/layout`);
  return data;
}

export async function getReservedTableIds(
  branchId: string,
  params: { date: string; start_time: string; end_time: string }
): Promise<string[]> {
  const { data } = await api.get<string[]>(`/branches/${branchId}/reserved-tables`, {
    params,
  });
  return data;
}


export async function getGuestMe(): Promise<GuestMeResponse> {
  const { data } = await api.get<GuestMeResponse>('/guest/me');
  return data;
}

export async function createReservation(body: ReservationCreate): Promise<ReservationResponse> {
  const { data } = await api.post<ReservationResponse>('/reservations', body);
  return data;
}

export async function getReservationsMe(): Promise<ReservationResponse[]> {
  const { data } = await api.get<ReservationResponse[]>('/reservations/me', {
    withCredentials: true,
  });
  return data;
}

export async function getReservation(
  reservationId: string,
  code?: string
): Promise<ReservationResponse> {
  const params = code ? { code } : undefined;
  const { data } = await api.get<ReservationResponse>(`/reservations/${reservationId}`, {
    params,
  });
  return data;
}

/** Link reservation to current guest (by id+code) so it appears in My Reservations. */
export async function attachReservationToGuest(
  reservationId: string,
  code: string
): Promise<ReservationResponse> {
  const { data } = await api.post<ReservationResponse>(
    `/reservations/${reservationId}/attach`,
    undefined,
    { params: { code } }
  );
  return data;
}

/** [Development only] Link reservation to current guest by ID (no code). For local testing. */
export async function devAttachReservationToGuest(
  reservationId: string
): Promise<ReservationResponse> {
  const { data } = await api.post<ReservationResponse>(
    `/reservations/dev/attach/${reservationId}`
  );
  return data;
}

export async function confirmReservation(
  reservationId: string,
  token: string
): Promise<ReservationResponse> {
  const { data } = await api.get<ReservationResponse>(
    `/reservations/${reservationId}/confirm`,
    { params: { token } }
  );
  return data;
}

export async function cancelReservation(
  reservationId: string,
  token: string
): Promise<ReservationResponse> {
  const { data } = await api.get<ReservationResponse>(
    `/reservations/${reservationId}/cancel`,
    { params: { token } }
  );
  return data;
}

// —— Admin (auth required) ——

export async function listBranches(params?: {
  page?: number;
  page_size?: number;
}): Promise<PaginatedResponse<BranchResponse>> {
  const { data } = await api.get<PaginatedResponse<BranchResponse>>('/admin/branches', {
    params: params ?? {},
  });
  return data;
}

export async function createBranch(body: BranchCreate): Promise<BranchResponse> {
  const { data } = await api.post<BranchResponse>('/admin/branches', body);
  return data;
}

export async function updateBranch(
  branchId: string,
  body: BranchUpdate
): Promise<BranchResponse> {
  const { data } = await api.patch<BranchResponse>(`/admin/branches/${branchId}`, body);
  return data;
}

export async function listTables(params?: {
  branch_id?: string;
  page?: number;
  page_size?: number;
}): Promise<PaginatedResponse<TableResponse>> {
  const { data } = await api.get<PaginatedResponse<TableResponse>>('/admin/tables', {
    params: params ?? {},
  });
  return data;
}

export async function createTable(body: TableCreate): Promise<TableResponse> {
  const { data } = await api.post<TableResponse>('/admin/tables', body);
  return data;
}

export async function updateTable(
  tableId: string,
  body: TableUpdate
): Promise<TableResponse> {
  const { data } = await api.patch<TableResponse>(`/admin/tables/${tableId}`, body);
  return data;
}

export async function deleteTable(tableId: string): Promise<void> {
  await api.delete(`/admin/tables/${tableId}`);
}

export async function listReservations(params?: {
  branch_id?: string;
  date?: string;
  status?: string;
  phone_number?: string;
  page?: number;
  page_size?: number;
  sort_by?: string;
  order?: string;
}): Promise<PaginatedResponse<ReservationResponse>> {
  const { data } = await api.get<PaginatedResponse<ReservationResponse>>(
    '/admin/reservations',
    { params: params ?? {} }
  );
  return data;
}

export async function getAdminReservation(
  reservationId: string,
  code?: string
): Promise<ReservationResponse> {
  const params = code ? { code } : undefined;
  const { data } = await api.get<ReservationResponse>(
    `/admin/reservations/${reservationId}`,
    { params }
  );
  return data;
}

export async function updateReservation(
  reservationId: string,
  body: ReservationUpdate
): Promise<ReservationResponse> {
  const { data } = await api.patch<ReservationResponse>(
    `/admin/reservations/${reservationId}`,
    body
  );
  return data;
}

export async function getDashboardStats(params?: {
  branch_id?: string;
  from_date?: string;
  to_date?: string;
}): Promise<{ data: DashboardStats }> {
  const { data } = await api.get<{ data: DashboardStats }>('/admin/dashboard/stats', {
    params: params ?? {},
  });
  return data;
}

export async function getLayout(branchId: string): Promise<LayoutDocument> {
  const { data } = await api.get<LayoutDocument>(`/admin/branches/${branchId}/layout`);
  return data;
}

export async function saveLayout(branchId: string, layout: LayoutDocument): Promise<LayoutDocument> {
  const { data } = await api.put<LayoutDocument>(`/admin/branches/${branchId}/layout`, layout);
  return data;
}
