import { create } from 'zustand';
import type { Layout, LayoutTable, LayoutDocument } from '@/lib/types';
import { isLayoutV1 } from '@/lib/types';
import { getLayout, saveLayout } from '@/lib/api';

const GRID_SIZE = 10;

/** Generate a UUID v4; works in all browsers (uses getRandomValues, not randomUUID). */
function generateUUID(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  const bytes = new Uint8Array(16);
  if (typeof crypto !== 'undefined' && typeof crypto.getRandomValues === 'function') {
    crypto.getRandomValues(bytes);
  } else {
    for (let i = 0; i < 16; i++) bytes[i] = Math.floor(Math.random() * 256);
  }
  bytes[6] = (bytes[6]! & 0x0f) | 0x40;
  bytes[8] = (bytes[8]! & 0x3f) | 0x80;
  const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

function snapToGrid(value: number): number {
  return Math.round(value / GRID_SIZE) * GRID_SIZE;
}

export interface FloorEditorState {
  layout: Layout;
  selectedId: string | null;
  branchId: string | null;
  isSaving: boolean;
}

export interface FloorEditorActions {
  setLayout: (layout: Layout) => void;
  setSelectedId: (id: string | null) => void;
  setBranchId: (id: string | null) => void;
  addTable: (shape: 'round' | 'rect') => void;
  updateTable: (
    id: string,
    patch: Partial<Pick<LayoutTable, 'x' | 'y' | 'width' | 'height' | 'rotation' | 'capacity' | 'table_number' | 'shape'>>
  ) => void;
  deleteTable: (id: string) => void;
  loadLayout: (branchId: string) => Promise<void>;
  saveLayoutToApi: (branchId: string) => Promise<void>;
  reset: () => void;
}

const defaultLayout: Layout = {
  width: 800,
  height: 600,
  tables: [],
};

const initialState: FloorEditorState = {
  layout: defaultLayout,
  selectedId: null,
  branchId: null,
  isSaving: false,
};

export const useFloorEditorStore = create<FloorEditorState & FloorEditorActions>((set, get) => ({
  ...initialState,

  setLayout: (layout) => set({ layout }),

  setSelectedId: (selectedId) => set({ selectedId }),

  setBranchId: (branchId) => set({ branchId }),

  addTable: (shape) => {
    const { layout } = get();
    const id = generateUUID();
    const newTable: LayoutTable = {
      id,
      x: 100 + layout.tables.length * 20,
      y: 100 + layout.tables.length * 20,
      width: shape === 'round' ? 60 : 80,
      height: shape === 'round' ? 60 : 60,
      rotation: 0,
      shape,
      capacity: 2,
      table_number: `T${layout.tables.length + 1}`,
    };
    set({
      layout: {
        ...layout,
        tables: [...layout.tables, newTable],
      },
      selectedId: id,
    });
  },

  updateTable: (id, patch) => {
    const { layout } = get();
    const tables = layout.tables.map((t) => {
      if (t.id !== id) return t;
      const next = { ...t, ...patch };
      if (patch.x !== undefined) next.x = Math.max(0, snapToGrid(patch.x));
      if (patch.y !== undefined) next.y = Math.max(0, snapToGrid(patch.y));
      if (patch.width !== undefined) next.width = Math.max(GRID_SIZE, snapToGrid(patch.width));
      if (patch.height !== undefined) next.height = Math.max(GRID_SIZE, snapToGrid(patch.height));
      if (patch.rotation !== undefined) next.rotation = patch.rotation;
      return next;
    });
    set({ layout: { ...layout, tables } });
  },

  deleteTable: (id) => {
    const { layout, selectedId } = get();
    set({
      layout: {
        ...layout,
        tables: layout.tables.filter((t) => t.id !== id),
      },
      selectedId: selectedId === id ? null : selectedId,
    });
  },

  loadLayout: async (branchId) => {
    try {
      const layoutDoc = await getLayout(branchId);
      // Convert to v1 for backward compatibility
      const layout: Layout = isLayoutV1(layoutDoc)
        ? layoutDoc
        : { width: 800, height: 600, tables: [] };
      set({ layout, branchId, selectedId: null });
    } catch {
      set({
        layout: { width: 800, height: 600, tables: [] },
        branchId,
        selectedId: null,
      });
    }
  },

  saveLayoutToApi: async (branchId) => {
    const { layout } = get();
    set({ isSaving: true });
    try {
      const saved = await saveLayout(branchId, layout);
      // Convert back to v1 for backward compatibility
      const layoutV1: Layout = isLayoutV1(saved)
        ? saved
        : { width: 800, height: 600, tables: [] };
      set({ layout: layoutV1, isSaving: false });
    } catch (e) {
      set({ isSaving: false });
      throw e;
    }
  },

  reset: () => set(initialState),
}));

export function selectSelectedTable(state: FloorEditorState): LayoutTable | null {
  if (!state.selectedId) return null;
  return state.layout.tables.find((t) => t.id === state.selectedId) ?? null;
}
