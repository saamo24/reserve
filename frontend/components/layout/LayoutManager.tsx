'use client';

import React, { useRef, useState, useEffect, useCallback } from 'react';
import { useLayoutBuilderStore, selectActiveZone, selectActiveFloor, selectActiveTables } from '@/stores/layoutBuilderStore';
import { FloorCanvas } from './FloorCanvas';
import { ZoneTabs } from './ZoneTabs';
import { FloorTabs } from './FloorTabs';
import { AdminSidebar } from './AdminSidebar';

export function LayoutManager() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 800, height: 600 });

  const layoutV2 = useLayoutBuilderStore((s) => s.layoutV2);
  const activeZoneId = useLayoutBuilderStore((s) => s.activeZoneId);
  const activeFloorId = useLayoutBuilderStore((s) => s.activeFloorId);
  const selectedTableId = useLayoutBuilderStore((s) => s.selectedTableId);
  const activeZone = useLayoutBuilderStore(selectActiveZone);
  const activeFloor = useLayoutBuilderStore(selectActiveFloor);
  const activeTables = useLayoutBuilderStore(selectActiveTables);

  const setActiveZoneId = useLayoutBuilderStore((s) => s.setActiveZoneId);
  const setActiveFloorId = useLayoutBuilderStore((s) => s.setActiveFloorId);
  const setSelectedTableId = useLayoutBuilderStore((s) => s.setSelectedTableId);
  const updateTable = useLayoutBuilderStore((s) => s.updateTable);
  const addZone = useLayoutBuilderStore((s) => s.addZone);
  const updateZone = useLayoutBuilderStore((s) => s.updateZone);
  const deleteZone = useLayoutBuilderStore((s) => s.deleteZone);
  const addFloor = useLayoutBuilderStore((s) => s.addFloor);
  const updateFloor = useLayoutBuilderStore((s) => s.updateFloor);
  const deleteFloor = useLayoutBuilderStore((s) => s.deleteFloor);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const updateSize = () => {
      const w = el.offsetWidth || 800;
      const h = el.offsetHeight || 600;
      setSize({ width: w, height: h });
    };
    updateSize();
    const ro = new ResizeObserver(updateSize);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const handleDragEnd = useCallback(
    (id: string, x: number, y: number) => {
      updateTable(id, { x, y });
    },
    [updateTable]
  );

  const handleTransformEnd = useCallback(
    (
      id: string,
      attrs: { x: number; y: number; width: number; height: number; rotation: number }
    ) => {
      updateTable(id, attrs);
    },
    [updateTable]
  );

  const handleRenameZone = useCallback(
    (zoneId: string, name: string) => {
      updateZone(zoneId, { name });
    },
    [updateZone]
  );

  const handleRenameFloor = useCallback(
    (floorId: string, name: string) => {
      if (!activeZoneId) return;
      updateFloor(activeZoneId, floorId, { name });
    },
    [activeZoneId, updateFloor]
  );

  // Get canvas dimensions
  const canvasWidth = activeZone?.type === 'outdoor' ? (activeZone.width || 800) : (activeFloor?.width || 800);
  const canvasHeight = activeZone?.type === 'outdoor' ? (activeZone.height || 600) : (activeFloor?.height || 600);

  const containerWidth = size.width >= 100 ? size.width : 800;
  const containerHeight = size.height >= 100 ? size.height : 600;

  if (layoutV2.zones.length === 0) {
    return (
      <div className="flex flex-1 min-h-0">
        <AdminSidebar />
        <div className="flex-1 flex items-center justify-center bg-secondary-50">
          <div className="text-center">
            <p className="text-secondary-600 mb-4">No zones yet. Add a zone to start building your layout.</p>
            <button
              onClick={() => addZone('indoor')}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 mr-2"
            >
              Add Indoor Zone
            </button>
            <button
              onClick={() => addZone('outdoor')}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
            >
              Add Outdoor Zone
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col flex-1 min-h-0">
      <ZoneTabs
        zones={layoutV2.zones}
        activeZoneId={activeZoneId}
        onSelectZone={setActiveZoneId}
        onAddZone={addZone}
        onDeleteZone={deleteZone}
        onRenameZone={handleRenameZone}
      />
      {activeZone?.type === 'indoor' && activeZone.floors && (
        <FloorTabs
          floors={activeZone.floors}
          activeFloorId={activeFloorId}
          onSelectFloor={setActiveFloorId}
          onAddFloor={() => activeZoneId && addFloor(activeZoneId)}
          onDeleteFloor={(floorId) => activeZoneId && deleteFloor(activeZoneId, floorId)}
          onRenameFloor={handleRenameFloor}
        />
      )}
      <div className="flex flex-1 min-h-0 gap-0">
        <AdminSidebar />
        <div ref={containerRef} className="flex-1 min-w-0 min-h-0 bg-secondary-100">
          <FloorCanvas
            tables={activeTables}
            width={canvasWidth}
            height={canvasHeight}
            mode="admin"
            selectedId={selectedTableId}
            containerWidth={containerWidth}
            containerHeight={containerHeight}
            onSelect={setSelectedTableId}
            onDragEnd={handleDragEnd}
            onTransformEnd={handleTransformEnd}
          />
        </div>
      </div>
    </div>
  );
}
