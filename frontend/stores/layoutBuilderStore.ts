import { create } from 'zustand';
import type {
  LayoutV2,
  LayoutZone,
  LayoutFloor,
  LayoutTable,
  ZoneType,
} from '@/lib/types';
import { getLayout, saveLayout } from '@/lib/api';
import { normalizeLayoutToV2 } from '@/lib/utils';

const GRID_SIZE = 10;

/** Generate a UUID v4. */
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

export interface LayoutBuilderState {
  layoutV2: LayoutV2;
  activeZoneId: string | null;
  activeFloorId: string | null;
  selectedTableId: string | null;
  branchId: string | null;
  isSaving: boolean;
}

export interface LayoutBuilderActions {
  setLayoutV2: (layout: LayoutV2) => void;
  setActiveZoneId: (zoneId: string | null) => void;
  setActiveFloorId: (floorId: string | null) => void;
  setSelectedTableId: (tableId: string | null) => void;
  setBranchId: (branchId: string | null) => void;
  
  // Zone management
  addZone: (type: ZoneType, name?: string) => string;
  updateZone: (zoneId: string, updates: Partial<Pick<LayoutZone, 'name' | 'type' | 'width' | 'height'>>) => void;
  deleteZone: (zoneId: string) => void;
  
  // Floor management (indoor only)
  addFloor: (zoneId: string, name?: string) => string;
  updateFloor: (zoneId: string, floorId: string, updates: Partial<Pick<LayoutFloor, 'name' | 'width' | 'height'>>) => void;
  deleteFloor: (zoneId: string, floorId: string) => void;
  
  // Table management
  addTable: (shape: 'round' | 'rect') => void;
  updateTable: (
    tableId: string,
    patch: Partial<Pick<LayoutTable, 'x' | 'y' | 'width' | 'height' | 'rotation' | 'capacity' | 'table_number' | 'shape'>>
  ) => void;
  deleteTable: (tableId: string) => void;
  
  // Load/save
  loadLayout: (branchId: string) => Promise<void>;
  saveLayoutToApi: (branchId: string) => Promise<void>;
  reset: () => void;
}

const defaultLayoutV2: LayoutV2 = {
  zones: [],
};

const initialState: LayoutBuilderState = {
  layoutV2: defaultLayoutV2,
  activeZoneId: null,
  activeFloorId: null,
  selectedTableId: null,
  branchId: null,
  isSaving: false,
};

export const useLayoutBuilderStore = create<LayoutBuilderState & LayoutBuilderActions>(
  (set, get) => ({
    ...initialState,

    setLayoutV2: (layoutV2) => {
      set({ layoutV2 });
      // Auto-select first zone/floor if available
      if (layoutV2.zones.length > 0) {
        const firstZone = layoutV2.zones[0]!;
        set({ activeZoneId: firstZone.id });
        if (firstZone.type === 'indoor' && firstZone.floors && firstZone.floors.length > 0) {
          set({ activeFloorId: firstZone.floors[0]!.id });
        } else {
          set({ activeFloorId: null });
        }
      }
    },

    setActiveZoneId: (zoneId) => {
      const { layoutV2 } = get();
      const zone = layoutV2.zones.find((z) => z.id === zoneId);
      set({ activeZoneId: zoneId });
      // Auto-select first floor if indoor
      if (zone?.type === 'indoor' && zone.floors && zone.floors.length > 0) {
        set({ activeFloorId: zone.floors[0]!.id });
      } else {
        set({ activeFloorId: null });
      }
      set({ selectedTableId: null });
    },

    setActiveFloorId: (floorId) => {
      set({ activeFloorId: floorId, selectedTableId: null });
    },

    setSelectedTableId: (tableId) => set({ selectedTableId: tableId }),

    setBranchId: (branchId) => set({ branchId }),

    addZone: (type, name) => {
      const { layoutV2 } = get();
      const zoneId = generateUUID();
      const zoneName = name || (type === 'indoor' ? 'Indoor' : 'Outdoor');
      
      const newZone: LayoutZone = {
        id: zoneId,
        name: zoneName,
        type,
        ...(type === 'indoor'
          ? {
              floors: [
                {
                  id: generateUUID(),
                  name: 'Floor 1',
                  width: 800,
                  height: 600,
                  tables: [],
                },
              ],
            }
          : {
              width: 800,
              height: 600,
              tables: [],
            }),
      };
      
      set({
        layoutV2: {
          zones: [...layoutV2.zones, newZone],
        },
        activeZoneId: zoneId,
        activeFloorId: type === 'indoor' && newZone.floors ? newZone.floors[0]!.id : null,
      });
      
      return zoneId;
    },

    updateZone: (zoneId, updates) => {
      const { layoutV2 } = get();
      const zones = layoutV2.zones.map((z) => {
        if (z.id !== zoneId) return z;
        const updated = { ...z, ...updates };
        // Ensure outdoor zones have required fields
        if (updated.type === 'outdoor') {
          updated.width = updated.width ?? 800;
          updated.height = updated.height ?? 600;
          updated.tables = updated.tables ?? [];
          updated.floors = undefined;
        }
        return updated;
      });
      set({ layoutV2: { zones } });
    },

    deleteZone: (zoneId) => {
      const { layoutV2, activeZoneId } = get();
      const zones = layoutV2.zones.filter((z) => z.id !== zoneId);
      set({
        layoutV2: { zones },
        activeZoneId: activeZoneId === zoneId ? (zones.length > 0 ? zones[0]!.id : null) : activeZoneId,
        activeFloorId: null,
        selectedTableId: null,
      });
    },

    addFloor: (zoneId, name) => {
      const { layoutV2 } = get();
      const floorId = generateUUID();
      const floorName = name || `Floor ${(layoutV2.zones.find((z) => z.id === zoneId)?.floors?.length ?? 0) + 1}`;
      
      const zones = layoutV2.zones.map((z) => {
        if (z.id !== zoneId || z.type !== 'indoor') return z;
        const floors = z.floors || [];
        return {
          ...z,
          floors: [
            ...floors,
            {
              id: floorId,
              name: floorName,
              width: 800,
              height: 600,
              tables: [],
            },
          ],
        };
      });
      
      set({
        layoutV2: { zones },
        activeFloorId: floorId,
      });
      
      return floorId;
    },

    updateFloor: (zoneId, floorId, updates) => {
      const { layoutV2 } = get();
      const zones = layoutV2.zones.map((z) => {
        if (z.id !== zoneId || z.type !== 'indoor' || !z.floors) return z;
        return {
          ...z,
          floors: z.floors.map((f) => (f.id === floorId ? { ...f, ...updates } : f)),
        };
      });
      set({ layoutV2: { zones } });
    },

    deleteFloor: (zoneId, floorId) => {
      const { layoutV2, activeFloorId } = get();
      const zones = layoutV2.zones.map((z) => {
        if (z.id !== zoneId || z.type !== 'indoor' || !z.floors) return z;
        const floors = z.floors.filter((f) => f.id !== floorId);
        if (floors.length === 0) {
          // Can't delete last floor, keep it
          return z;
        }
        return { ...z, floors };
      });
      set({
        layoutV2: { zones },
        activeFloorId: activeFloorId === floorId ? null : activeFloorId,
        selectedTableId: null,
      });
    },

    addTable: (shape) => {
      const { layoutV2, activeZoneId, activeFloorId } = get();
      if (!activeZoneId) return;
      
      const zone = layoutV2.zones.find((z) => z.id === activeZoneId);
      if (!zone) return;
      
      const tableId = generateUUID();
      const newTable: LayoutTable = {
        id: tableId,
        x: 100,
        y: 100,
        width: shape === 'round' ? 60 : 80,
        height: shape === 'round' ? 60 : 60,
        rotation: 0,
        shape,
        capacity: 2,
        table_number: `T${Date.now()}`,
      };
      
      if (zone.type === 'indoor') {
        if (!activeFloorId || !zone.floors) return;
        const zones = layoutV2.zones.map((z) => {
          if (z.id !== activeZoneId || !z.floors) return z;
          return {
            ...z,
            floors: z.floors.map((f) =>
              f.id === activeFloorId ? { ...f, tables: [...f.tables, newTable] } : f
            ),
          };
        });
        set({
          layoutV2: { zones },
          selectedTableId: tableId,
        });
      } else {
        // Outdoor
        const zones = layoutV2.zones.map((z) =>
          z.id === activeZoneId ? { ...z, tables: [...(z.tables || []), newTable] } : z
        );
        set({
          layoutV2: { zones },
          selectedTableId: tableId,
        });
      }
    },

    updateTable: (tableId, patch) => {
      const { layoutV2 } = get();
      const zones = layoutV2.zones.map((z) => {
        if (z.type === 'indoor' && z.floors) {
          return {
            ...z,
            floors: z.floors.map((f) => ({
              ...f,
              tables: f.tables.map((t) => {
                if (t.id !== tableId) return t;
                const next = { ...t, ...patch };
                if (patch.x !== undefined) next.x = Math.max(0, snapToGrid(patch.x));
                if (patch.y !== undefined) next.y = Math.max(0, snapToGrid(patch.y));
                if (patch.width !== undefined) next.width = Math.max(GRID_SIZE, snapToGrid(patch.width));
                if (patch.height !== undefined) next.height = Math.max(GRID_SIZE, snapToGrid(patch.height));
                return next;
              }),
            })),
          };
        } else {
          // Outdoor
          return {
            ...z,
            tables: (z.tables || []).map((t) => {
              if (t.id !== tableId) return t;
              const next = { ...t, ...patch };
              if (patch.x !== undefined) next.x = Math.max(0, snapToGrid(patch.x));
              if (patch.y !== undefined) next.y = Math.max(0, snapToGrid(patch.y));
              if (patch.width !== undefined) next.width = Math.max(GRID_SIZE, snapToGrid(patch.width));
              if (patch.height !== undefined) next.height = Math.max(GRID_SIZE, snapToGrid(patch.height));
              return next;
            }),
          };
        }
      });
      set({ layoutV2: { zones } });
    },

    deleteTable: (tableId) => {
      const { layoutV2, selectedTableId } = get();
      const zones = layoutV2.zones.map((z) => {
        if (z.type === 'indoor' && z.floors) {
          return {
            ...z,
            floors: z.floors.map((f) => ({
              ...f,
              tables: f.tables.filter((t) => t.id !== tableId),
            })),
          };
        } else {
          return {
            ...z,
            tables: (z.tables || []).filter((t) => t.id !== tableId),
          };
        }
      });
      set({
        layoutV2: { zones },
        selectedTableId: selectedTableId === tableId ? null : selectedTableId,
      });
    },

    loadLayout: async (branchId) => {
      try {
        const layout = await getLayout(branchId);
        const layoutV2 = normalizeLayoutToV2(layout);
        set({ layoutV2, branchId, selectedTableId: null });
        
        // Auto-select first zone/floor
        if (layoutV2.zones.length > 0) {
          const firstZone = layoutV2.zones[0]!;
          set({ activeZoneId: firstZone.id });
          if (firstZone.type === 'indoor' && firstZone.floors && firstZone.floors.length > 0) {
            set({ activeFloorId: firstZone.floors[0]!.id });
          } else {
            set({ activeFloorId: null });
          }
        }
      } catch {
        set({
          layoutV2: defaultLayoutV2,
          branchId,
          selectedTableId: null,
          activeZoneId: null,
          activeFloorId: null,
        });
      }
    },

    saveLayoutToApi: async (branchId) => {
      const { layoutV2 } = get();
      set({ isSaving: true });
      try {
        const saved = await saveLayout(branchId, layoutV2);
        const savedV2 = normalizeLayoutToV2(saved);
        set({ layoutV2: savedV2, isSaving: false });
      } catch (e) {
        set({ isSaving: false });
        throw e;
      }
    },

    reset: () => set(initialState),
  })
);

// Selector helpers
export function selectActiveZone(state: LayoutBuilderState): LayoutZone | null {
  if (!state.activeZoneId) return null;
  return state.layoutV2.zones.find((z) => z.id === state.activeZoneId) ?? null;
}

export function selectActiveFloor(state: LayoutBuilderState): LayoutFloor | null {
  const zone = selectActiveZone(state);
  if (!zone || zone.type !== 'indoor' || !state.activeFloorId || !zone.floors) return null;
  return zone.floors.find((f) => f.id === state.activeFloorId) ?? null;
}

export function selectActiveTables(state: LayoutBuilderState): LayoutTable[] {
  const zone = selectActiveZone(state);
  if (!zone) return [];
  
  if (zone.type === 'indoor') {
    const floor = selectActiveFloor(state);
    return floor ? floor.tables : [];
  } else {
    return zone.tables || [];
  }
}

export function selectSelectedTable(state: LayoutBuilderState): LayoutTable | null {
  if (!state.selectedTableId) return null;
  const tables = selectActiveTables(state);
  return tables.find((t) => t.id === state.selectedTableId) ?? null;
}
