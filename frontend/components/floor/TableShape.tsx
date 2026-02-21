'use client';

import React, { useCallback, forwardRef } from 'react';
import { Group, Rect, Circle, Text } from 'react-konva';
import type Konva from 'konva';
import type { LayoutTable } from '@/lib/types';
import type { TableStatus } from '@/lib/types';

const FILL_AVAILABLE = '#22c55e';
const FILL_RESERVED = '#ef4444';
const FILL_DISABLED = '#9ca3af';
const FILL_EDITOR = '#e5e7eb';
const STROKE_SELECTED = '#3b82f6';
const STROKE_DEFAULT = '#6b7280';

export interface TableShapeProps {
  table: LayoutTable;
  isSelected?: boolean;
  status?: TableStatus;
  draggable?: boolean;
  onSelect?: (id: string) => void;
  onDragEnd?: (id: string, x: number, y: number) => void;
}

export const TableShape = forwardRef<Konva.Group, TableShapeProps>(
  function TableShape(
    {
      table,
      isSelected = false,
      status,
      draggable = false,
      onSelect,
      onDragEnd,
    },
    ref
  ) {
  const cx = table.x + table.width / 2;
  const cy = table.y + table.height / 2;

  const handleClick = useCallback(() => {
    onSelect?.(table.id);
  }, [table.id, onSelect]);

  const handleDragEnd = useCallback(
    (e: { target: { x: () => number; y: () => number } }) => {
      const node = e.target;
      const newX = node.x() - table.width / 2;
      const newY = node.y() - table.height / 2;
      onDragEnd?.(table.id, newX, newY);
    },
    [table.id, table.width, table.height, onDragEnd]
  );

  const fill =
    status === 'available'
      ? FILL_AVAILABLE
      : status === 'reserved'
        ? FILL_RESERVED
        : status === 'disabled'
          ? FILL_DISABLED
          : FILL_EDITOR;

  const stroke = isSelected ? STROKE_SELECTED : STROKE_DEFAULT;
  const strokeWidth = isSelected ? 3 : 1;

  return (
    <Group
      ref={ref}
      id={table.id}
      x={cx}
      y={cy}
      rotation={table.rotation}
      draggable={draggable}
      onDragEnd={handleDragEnd}
      onClick={handleClick}
      onTap={handleClick}
      listening={true}
    >
      {table.shape === 'round' ? (
        <Circle
          x={0}
          y={0}
          radius={Math.min(table.width, table.height) / 2}
          fill={fill}
          stroke={stroke}
          strokeWidth={strokeWidth}
        />
      ) : (
        <Rect
          x={-table.width / 2}
          y={-table.height / 2}
          width={table.width}
          height={table.height}
          fill={fill}
          stroke={stroke}
          strokeWidth={strokeWidth}
        />
      )}
      <Text
        x={-table.width / 2}
        y={-table.height / 2}
        width={table.width}
        height={table.height}
        text={table.table_number}
        fontSize={14}
        fontStyle="bold"
        align="center"
        verticalAlign="middle"
        listening={false}
      />
    </Group>
  );
  }
);
