'use client';

import React, { useState, useCallback, useEffect, useMemo } from 'react';
import { getLayoutPublic, getReservedTableIds, getBranchTables } from '@/lib/api';
import type { Layout, TableStatus } from '@/lib/types';
import { FloorCanvas } from './FloorCanvas';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { LoadingSpinner } from '@/components/ui/loading';

interface UserTableSelectorProps {
  branchId: string;
  /** Selected date YYYY-MM-DD */
  date: string;
  /** Slot start time (e.g. "14:00") */
  startTime: string;
  /** Slot end time (e.g. "16:00") */
  endTime: string;
  selectedTableId: string | null;
  onSelectTable: (tableId: string | null, table: import('@/lib/types').LayoutTable | null) => void;
  containerWidth: number;
  containerHeight: number;
}

export function UserTableSelector({
  branchId,
  date,
  startTime,
  endTime,
  selectedTableId,
  onSelectTable,
  containerWidth,
  containerHeight,
}: UserTableSelectorProps) {
  const [layout, setLayout] = useState<Layout | null>(null);
  const [reservedIds, setReservedIds] = useState<Set<string>>(new Set());
  const [activeTableIds, setActiveTableIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
        setLayout(layoutData);
        setReservedIds(new Set(reserved));
        setActiveTableIds(new Set(tables.map((t) => t.id)));
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

  const tableStatuses = useMemo(() => {
    const map = new Map<string, TableStatus>();
    if (!layout) return map;
    for (const t of layout.tables) {
      if (!activeTableIds.has(t.id)) {
        map.set(t.id, 'disabled');
      } else if (reservedIds.has(t.id)) {
        map.set(t.id, 'reserved');
      } else {
        map.set(t.id, 'available');
      }
    }
    return map;
  }, [layout, reservedIds, activeTableIds]);

  const handleSelect = useCallback(
    (id: string) => {
      if (!layout) return;
      const status = tableStatuses.get(id);
      if (status !== 'available') return;
      if (selectedTableId === id) {
        onSelectTable(null, null);
        return;
      }
      const table = layout.tables.find((t) => t.id === id) ?? null;
      onSelectTable(id, table);
    },
    [layout, tableStatuses, selectedTableId, onSelectTable]
  );

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

  if (layout.tables.length === 0) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-secondary-600">No tables in this layout.</p>
        </CardContent>
      </Card>
    );
  }

  // Calculate a reasonable canvas size that shows the layout well
  // Use the container size as base, but ensure it's at least as large as the layout
  // Add some padding for better visibility
  const padding = 40;
  const minCanvasWidth = Math.max(layout.width + padding, 400);
  const minCanvasHeight = Math.max(layout.height + padding, 300);
  
  // Use container size if it's larger, otherwise use calculated minimum
  const canvasWidth = Math.max(containerWidth, minCanvasWidth);
  const canvasHeight = Math.max(containerHeight, minCanvasHeight);
  
  // For mobile, use a reasonable viewport-relative max height with scrolling
  const maxContainerHeight = '70vh';
  
  return (
    <Card>
      <CardHeader className="px-4 sm:px-6">
        <CardTitle className="text-lg sm:text-xl">Select a table</CardTitle>
        <p className="text-xs sm:text-sm text-secondary-600 mt-1">
          Green: available · Red: reserved · Click a green table to select
        </p>
      </CardHeader>
      <CardContent className="px-4 sm:px-6 pb-4 sm:pb-6">
        <div 
          className="rounded-lg border border-secondary-200 overflow-auto bg-secondary-50" 
          style={{ 
            maxHeight: maxContainerHeight, 
            minHeight: '300px',
            width: '100%'
          }}
        >
          <div style={{ width: canvasWidth, height: canvasHeight, position: 'relative' }}>
            <FloorCanvas
              layout={layout}
              mode="user"
              selectedId={selectedTableId}
              containerWidth={canvasWidth}
              containerHeight={canvasHeight}
              tableStatuses={tableStatuses}
              onSelectTable={handleSelect}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
