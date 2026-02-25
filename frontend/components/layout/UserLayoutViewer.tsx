'use client';

import React, { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import { getLayoutPublic, getReservedTableIds, getBranchTables } from '@/lib/api';
import type { LayoutDocument, LayoutV2, LayoutZone, LayoutFloor, LayoutTable, TableStatus } from '@/lib/types';
import { isLayoutV2 } from '@/lib/types';
import { normalizeLayoutToV2 } from '@/lib/utils';
import { FloorCanvas } from './FloorCanvas';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { LoadingSpinner } from '@/components/ui/loading';

interface UserLayoutViewerProps {
  branchId: string;
  /** Selected date YYYY-MM-DD */
  date: string;
  /** Slot start time (e.g. "14:00") */
  startTime: string;
  /** Slot end time (e.g. "16:00") */
  endTime: string;
  selectedTableId: string | null;
  onSelectTable: (tableId: string | null, table: LayoutTable | null, zoneId: string | null, floorId: string | null) => void;
  containerWidth: number;
  containerHeight: number;
}

export function UserLayoutViewer({
  branchId,
  date,
  startTime,
  endTime,
  selectedTableId,
  onSelectTable,
  containerWidth,
  containerHeight,
}: UserLayoutViewerProps) {
  const [layout, setLayout] = useState<LayoutV2 | null>(null);
  const [reservedIds, setReservedIds] = useState<Set<string>>(new Set());
  const [activeTableIds, setActiveTableIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedZoneId, setSelectedZoneId] = useState<string | null>(null);
  const [selectedFloorId, setSelectedFloorId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all([
      getLayoutPublic(branchId),
      getReservedTableIds(branchId, {
        date,
        start_time: startTime,
        end_time: endTime,
      }),
      getBranchTables(branchId),
    ])
      .then(([layoutData, reserved, tables]) => {
        if (cancelled) return;
        const layoutV2 = normalizeLayoutToV2(layoutData);
        setLayout(layoutV2);
        setReservedIds(new Set(reserved));
        setActiveTableIds(new Set(tables.map((t) => t.id)));
        
        // Auto-select first zone/floor
        if (layoutV2.zones.length > 0) {
          const firstZone = layoutV2.zones[0]!;
          setSelectedZoneId(firstZone.id);
          if (firstZone.type === 'indoor' && firstZone.floors && firstZone.floors.length > 0) {
            setSelectedFloorId(firstZone.floors[0]!.id);
          } else {
            setSelectedFloorId(null);
          }
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : 'Failed to load layout');
          setLayout(null);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [branchId, date, startTime, endTime]);

  const selectedZone = useMemo(() => {
    if (!layout || !selectedZoneId) return null;
    return layout.zones.find((z) => z.id === selectedZoneId) ?? null;
  }, [layout, selectedZoneId]);

  const selectedFloor = useMemo(() => {
    if (!selectedZone || selectedZone.type !== 'indoor' || !selectedFloorId || !selectedZone.floors) return null;
    return selectedZone.floors.find((f) => f.id === selectedFloorId) ?? null;
  }, [selectedZone, selectedFloorId]);

  const activeTables = useMemo(() => {
    if (!selectedZone) return [];
    if (selectedZone.type === 'outdoor') {
      return selectedZone.tables || [];
    } else if (selectedFloor) {
      return selectedFloor.tables;
    }
    return [];
  }, [selectedZone, selectedFloor]);

  const tableStatuses = useMemo(() => {
    const map = new Map<string, TableStatus>();
    for (const t of activeTables) {
      if (!activeTableIds.has(t.id)) {
        map.set(t.id, 'disabled');
      } else if (reservedIds.has(t.id)) {
        map.set(t.id, 'reserved');
      } else {
        map.set(t.id, 'available');
      }
    }
    return map;
  }, [activeTables, reservedIds, activeTableIds]);

  const handleSelectTable = useCallback(
    (id: string) => {
      if (!layout) return;
      const status = tableStatuses.get(id);
      if (status !== 'available') return;
      if (selectedTableId === id) {
        onSelectTable(null, null, null, null);
        return;
      }
      const table = activeTables.find((t) => t.id === id) ?? null;
      onSelectTable(id, table, selectedZoneId, selectedFloorId);
    },
    [layout, tableStatuses, selectedTableId, activeTables, selectedZoneId, selectedFloorId, onSelectTable]
  );

  const handleZoneSelect = useCallback((zoneId: string) => {
    setSelectedZoneId(zoneId);
    const zone = layout?.zones.find((z) => z.id === zoneId);
    if (zone?.type === 'indoor' && zone.floors && zone.floors.length > 0) {
      setSelectedFloorId(zone.floors[0]!.id);
    } else {
      setSelectedFloorId(null);
    }
    onSelectTable(null, null, null, null);
  }, [layout, onSelectTable]);

  const handleFloorSelect = useCallback((floorId: string) => {
    setSelectedFloorId(floorId);
    onSelectTable(null, null, null, null);
  }, [onSelectTable]);

  if (loading) {
    return (
      <Card>
        <CardContent className="p-12 flex justify-center">
          <LoadingSpinner size="lg" />
        </CardContent>
      </Card>
    );
  }

  if (error || !layout) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-secondary-600">
            {error ?? 'No floor plan available. Please choose a table from the list.'}
          </p>
        </CardContent>
      </Card>
    );
  }

  if (layout.zones.length === 0) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-secondary-600">No zones in this layout.</p>
        </CardContent>
      </Card>
    );
  }

  const canvasWidth = selectedZone?.type === 'outdoor' 
    ? (selectedZone.width || 800)
    : (selectedFloor?.width || 800);
  const canvasHeight = selectedZone?.type === 'outdoor'
    ? (selectedZone.height || 600)
    : (selectedFloor?.height || 600);

  const padding = 40;
  const minCanvasWidth = Math.max(canvasWidth + padding, 400);
  const minCanvasHeight = Math.max(canvasHeight + padding, 300);
  const finalCanvasWidth = Math.max(containerWidth, minCanvasWidth);
  const finalCanvasHeight = Math.max(containerHeight, minCanvasHeight);
  const maxContainerHeight = '70vh';

  return (
    <Card>
      <CardHeader className="px-4 sm:px-6">
        <CardTitle className="text-lg sm:text-xl">Select a table</CardTitle>
        <p className="text-xs sm:text-sm text-secondary-600 mt-1">
          Green: available · Red: reserved · Gray: disabled · Click a green table to select
        </p>
      </CardHeader>
      <CardContent className="px-4 sm:px-6 pb-4 sm:pb-6 space-y-4">
        {/* Zone Selection */}
        <div>
          <label className="block text-sm font-medium text-secondary-700 mb-2">Zone</label>
          <div className="flex gap-2 overflow-x-auto pb-2">
            {layout.zones.map((zone) => (
              <button
                key={zone.id}
                onClick={() => handleZoneSelect(zone.id)}
                className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors flex-shrink-0 ${
                  selectedZoneId === zone.id
                    ? 'bg-primary-600 text-white'
                    : 'bg-secondary-100 text-secondary-700 hover:bg-secondary-200'
                }`}
              >
                {zone.name}
              </button>
            ))}
          </div>
        </div>

        {/* Floor Selection (indoor only) */}
        {selectedZone?.type === 'indoor' && selectedZone.floors && selectedZone.floors.length > 0 && (
          <div>
            <label className="block text-sm font-medium text-secondary-700 mb-2">Floor</label>
            <div className="flex gap-2 overflow-x-auto pb-2">
              {selectedZone.floors.map((floor) => (
                <button
                  key={floor.id}
                  onClick={() => handleFloorSelect(floor.id)}
                  className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors flex-shrink-0 ${
                    selectedFloorId === floor.id
                      ? 'bg-primary-600 text-white'
                      : 'bg-white text-secondary-700 hover:bg-secondary-100 border border-secondary-300'
                  }`}
                >
                  {floor.name}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Canvas */}
        {activeTables.length === 0 ? (
          <div className="rounded-lg border border-secondary-200 bg-secondary-50 p-8 text-center">
            <p className="text-secondary-600">No tables in this {selectedZone?.type === 'indoor' ? 'floor' : 'zone'}.</p>
          </div>
        ) : (
          <div
            className="rounded-lg border border-secondary-200 overflow-auto bg-secondary-50"
            style={{
              maxHeight: maxContainerHeight,
              minHeight: '300px',
              width: '100%',
            }}
          >
            <div style={{ width: finalCanvasWidth, height: finalCanvasHeight, position: 'relative' }}>
              <FloorCanvas
                tables={activeTables}
                width={canvasWidth}
                height={canvasHeight}
                mode="user"
                selectedId={selectedTableId}
                containerWidth={finalCanvasWidth}
                containerHeight={finalCanvasHeight}
                tableStatuses={tableStatuses}
                onSelectTable={handleSelectTable}
              />
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
