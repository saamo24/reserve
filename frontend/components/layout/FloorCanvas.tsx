'use client';

import React, { useRef, useCallback } from 'react';
import { Stage, Layer, Group } from 'react-konva';
import type Konva from 'konva';
import type { LayoutTable, TableStatus } from '@/lib/types';
import { TableShape } from './TableShape';
import { TransformerWrapper } from '@/components/floor/Transformer';

const GRID_SIZE = 10;

function snapToGrid(v: number): number {
  return Math.round(v / GRID_SIZE) * GRID_SIZE;
}

interface FloorCanvasProps {
  tables: LayoutTable[];
  width: number;
  height: number;
  mode: 'admin' | 'user';
  selectedId: string | null;
  containerWidth: number;
  containerHeight: number;
  /** User mode: table id -> status */
  tableStatuses?: Map<string, TableStatus>;
  /** User mode: when user clicks an available table */
  onSelectTable?: (id: string) => void;
  /** Admin mode: when selection changes */
  onSelect?: (id: string | null) => void;
  /** Admin mode: when table is dragged */
  onDragEnd?: (id: string, x: number, y: number) => void;
  /** Admin mode: when transform ends (resize/rotate) */
  onTransformEnd?: (
    id: string,
    attrs: { x: number; y: number; width: number; height: number; rotation: number }
  ) => void;
}

export function FloorCanvas({
  tables,
  width,
  height,
  mode,
  selectedId,
  containerWidth,
  containerHeight,
  tableStatuses,
  onSelectTable,
  onSelect,
  onDragEnd,
  onTransformEnd,
}: FloorCanvasProps) {
  const stageRef = useRef<Konva.Stage>(null);
  const isAdmin = mode === 'admin';

  const safeW = Math.max(1, width);
  const safeH = Math.max(1, height);
  const scale =
    containerWidth > 0 && containerHeight > 0
      ? Math.min(containerWidth / safeW, containerHeight / safeH, 1)
      : 1;
  const offsetX = containerWidth > 0 ? (containerWidth / scale - width) / 2 : 0;
  const offsetY = containerHeight > 0 ? (containerHeight / scale - height) / 2 : 0;

  const handleStageClick = useCallback(
    (e: Konva.KonvaEventObject<MouseEvent>) => {
      if (e.target === e.target.getStage()) {
        onSelect?.(null);
      }
    },
    [onSelect]
  );

  const handleTransformEnd = useCallback(
    (node: Konva.Node) => {
      if (!selectedId || !onTransformEnd) return;
      const table = tables.find((t) => t.id === selectedId);
      if (!table) return;
      const g = node as Konva.Group;
      const w = table.width * g.scaleX();
      const h = table.height * g.scaleY();
      const x = g.x() - w / 2;
      const y = g.y() - h / 2;
      onTransformEnd(selectedId, {
        x: snapToGrid(x),
        y: snapToGrid(y),
        width: snapToGrid(Math.max(GRID_SIZE, w)),
        height: snapToGrid(Math.max(GRID_SIZE, h)),
        rotation: g.rotation(),
      });
    },
    [selectedId, onTransformEnd, tables]
  );

  return (
    <Stage
      ref={stageRef}
      width={containerWidth}
      height={containerHeight}
      onClick={handleStageClick}
      onTap={handleStageClick}
    >
      <Layer>
        <Group x={offsetX} y={offsetY} scaleX={scale} scaleY={scale}>
          {tables.map((table) => (
            <TableShape
              key={table.id}
              table={table}
              isSelected={selectedId === table.id}
              status={tableStatuses?.get(table.id)}
              draggable={isAdmin}
              onSelect={isAdmin ? onSelect ?? undefined : onSelectTable}
              onDragEnd={isAdmin ? onDragEnd : undefined}
            />
          ))}
          {isAdmin && (
            <TransformerWrapper
              stageRef={stageRef}
              selectedId={selectedId}
              enabled={true}
              onTransformEnd={handleTransformEnd}
            />
          )}
        </Group>
      </Layer>
    </Stage>
  );
}
