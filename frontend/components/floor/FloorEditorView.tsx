'use client';

import React, { useRef, useState, useEffect, useCallback } from 'react';
import { useFloorEditorStore } from '@/stores/floorEditorStore';
import { FloorCanvas } from './FloorCanvas';
import { FloorEditorSidebar } from './AdminSidebar';

export function FloorEditorView() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 800, height: 600 });

  const layout = useFloorEditorStore((s) => s.layout);
  const selectedId = useFloorEditorStore((s) => s.selectedId);
  const setSelectedId = useFloorEditorStore((s) => s.setSelectedId);
  const updateTable = useFloorEditorStore((s) => s.updateTable);

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

  const canvasWidth = size.width >= 100 ? size.width : 800;
  const canvasHeight = size.height >= 100 ? size.height : 600;

  return (
    <div className="flex flex-1 min-h-0 gap-0">
      <FloorEditorSidebar />
      <div ref={containerRef} className="flex-1 min-w-0 min-h-0 bg-secondary-100">
        <FloorCanvas
          layout={layout}
          mode="admin"
          selectedId={selectedId}
          containerWidth={canvasWidth}
          containerHeight={canvasHeight}
          onSelect={setSelectedId}
          onDragEnd={handleDragEnd}
          onTransformEnd={handleTransformEnd}
        />
      </div>
    </div>
  );
}
