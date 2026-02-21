'use client';

import React, { useEffect, useRef, useCallback } from 'react';
import { Transformer } from 'react-konva';
import type Konva from 'konva';

interface TransformerWrapperProps {
  stageRef: React.RefObject<Konva.Stage | null>;
  selectedId: string | null;
  enabled?: boolean;
  onTransformEnd?: (node: Konva.Node) => void;
}

export function TransformerWrapper({
  stageRef,
  selectedId,
  enabled = true,
  onTransformEnd,
}: TransformerWrapperProps) {
  const trRef = useRef<Konva.Transformer>(null);

  useEffect(() => {
    const tr = trRef.current;
    const stage = stageRef.current;
    if (!tr || !stage || !enabled) return;
    const node = selectedId ? stage.findOne('#' + selectedId) : null;
    tr.nodes(node ? [node] : []);
    tr.getLayer()?.batchDraw();
  }, [stageRef, selectedId, enabled]);

  const handleTransformEnd = useCallback(() => {
    const stage = stageRef.current;
    if (!stage || !selectedId || !onTransformEnd) return;
    const node = stage.findOne('#' + selectedId);
    if (node) onTransformEnd(node);
  }, [stageRef, selectedId, onTransformEnd]);

  if (!enabled || !selectedId) return null;

  return (
    <Transformer
      ref={trRef}
      rotateEnabled={true}
      enabledAnchors={['top-left', 'top-right', 'bottom-left', 'bottom-right']}
      boundBoxFunc={(oldBox, newBox) => {
        const minSize = 20;
        if (Math.abs(newBox.width) < minSize || Math.abs(newBox.height) < minSize) {
          return oldBox;
        }
        return newBox;
      }}
      onTransformEnd={handleTransformEnd}
    />
  );
}
