import {
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
  Background,
  BackgroundVariant,
  type Node,
  type Edge,
  type NodeProps,
  Handle,
  Position,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import clsx from "clsx";
import React, { useCallback, useEffect, useMemo, useState } from "react";

import { useMetroMapStore } from "../../store/useMetroMapStore";
import type { MetroMap, Station, Line } from "../../lib/metro-map/map";

// Scaling constants to match reference implementation
const X_UNIT = 160;
const Y_UNIT = 80;

type StationNodeData = {
  station: Station;
  lineColors: string[];
  isSelected: boolean;
  isLocationSelectMode: boolean;
  locationSelectColor: string | null;
  onClick?: (stationId: string) => void;
  onLocationSelect?: (x: number, y: number) => void;
};

type StationNodeType = Node<StationNodeData>;

function StationNode({ data, id }: NodeProps<StationNodeType>) {
  const { station, lineColors, isSelected, isLocationSelectMode, locationSelectColor } = data;

  const handleClick = useCallback(() => {
    if (data.onClick) {
      data.onClick(station.id);
    }
  }, [data, station.id]);

  const primaryColor = lineColors[0] || "#888";

  return (
    <div
      className={clsx(
        "station-node relative flex cursor-pointer flex-col items-center",
        isSelected && "station-node--selected",
        isLocationSelectMode && "station-node--location-select"
      )}
      onClick={handleClick}
      style={{ "--station-color": primaryColor } as React.CSSProperties}
    >
      <Handle type="target" position={Position.Top} className="invisible" />
      <Handle type="source" position={Position.Bottom} className="invisible" />

      {/* Station dot */}
      <div
        className={clsx(
          "station-dot relative h-4 w-4 rounded-full border-2 transition-all",
          isSelected
            ? "scale-125 border-white bg-blue-500 shadow-lg"
            : "border-white bg-gray-800 dark:bg-gray-200"
        )}
        style={{
          backgroundColor: isSelected ? "#3b82f6" : primaryColor,
          boxShadow: isSelected
            ? "0 0 0 3px rgba(59, 130, 246, 0.4)"
            : "0 1px 3px rgba(0,0,0,0.3)",
        }}
      />

      {/* Station label */}
      <div
        className={clsx(
          "station-label mt-1 whitespace-nowrap rounded px-1 py-0.5 text-xs font-medium",
          isSelected
            ? "bg-blue-500 text-white"
            : "bg-white/90 text-gray-800 dark:bg-gray-800/90 dark:text-gray-100"
        )}
        style={{
          textShadow: "0 1px 2px rgba(0,0,0,0.1)",
        }}
      >
        {station.name}
      </div>

      {/* Multi-line indicator */}
      {lineColors.length > 1 && (
        <div className="absolute -right-1 -top-1 flex gap-0.5">
          {lineColors.slice(1, 4).map((color, i) => (
            <div
              key={i}
              className="h-2 w-2 rounded-full border border-white"
              style={{ backgroundColor: color }}
            />
          ))}
        </div>
      )}
    </div>
  );
}

const nodeTypes = {
  station: StationNode,
};

function buildNodes(
  map: MetroMap,
  selectedStationIds: string[],
  isLocationSelectMode: boolean,
  locationSelectColor: string | null,
  onClick?: (stationId: string) => void
): StationNodeType[] {
  return map.stations
    .filter((station) => station.visible !== false)
    .map((station) => {
      const lineColors = station.lines
        .map((lineId) => map.lines.find(l => l.id === lineId)?.color)
        .filter((c): c is string => !!c);

      return {
        id: station.id,
        type: "station",
        position: { x: station.x * X_UNIT, y: station.y * Y_UNIT },
        data: {
          station,
          lineColors: lineColors.length > 0 ? lineColors : ["#888888"],
          isSelected: selectedStationIds.includes(station.id),
          isLocationSelectMode,
          locationSelectColor,
          onClick,
        },
      };
    });
}

function buildEdges(map: MetroMap): Edge[] {
  const edges: Edge[] = [];
  const stationMap = new Map(map.stations.map(s => [s.id, s]));

  map.lines.forEach((line) => {
    const visibleStations = line.stations.filter(
      (stationId) => stationMap.get(stationId)?.visible !== false
    );

    for (let i = 0; i < visibleStations.length - 1; i++) {
      const sourceId = visibleStations[i];
      const targetId = visibleStations[i + 1];

      edges.push({
        id: `${line.id}-${sourceId}-${targetId}`,
        source: sourceId,
        target: targetId,
        style: {
          stroke: line.color,
          strokeWidth: 4,
        },
        type: "straight",
      });
    }
  });

  return edges;
}

type MetroMapCanvasContentsProps = {
  onLocationSelect?: (x: number, y: number) => void;
};

function MetroMapCanvasContents({ onLocationSelect }: MetroMapCanvasContentsProps) {
  const reactFlow = useReactFlow();
  const map = useMetroMapStore((state) => state.map);
  const setReactFlow = useMetroMapStore((state) => state.setReactFlow);
  const selectedStationIds = useMetroMapStore((state) => state.selectedStationIds);
  const setSelectedStationIds = useMetroMapStore((state) => state.setSelectedStationIds);
  const interactionMode = useMetroMapStore((state) => state.interactionMode);
  const locationSelectLineId = useMetroMapStore((state) => state.locationSelectLineId);
  const scheme = useMetroMapStore((state) => state.scheme);

  useEffect(() => {
    setReactFlow(reactFlow);
  }, [reactFlow, setReactFlow]);

  const isLocationSelectMode = interactionMode === "location_select";
  const locationSelectColor = locationSelectLineId
    ? map?.lines.find(l => l.id === locationSelectLineId)?.color || "#0088cc"
    : null;

  const handleNodeClick = useCallback(
    (stationId: string) => {
      if (isLocationSelectMode) {
        return; // Don't select stations in location select mode
      }
      setSelectedStationIds(
        selectedStationIds.includes(stationId)
          ? selectedStationIds.filter((id) => id !== stationId)
          : [...selectedStationIds, stationId]
      );
    },
    [selectedStationIds, setSelectedStationIds, isLocationSelectMode]
  );

  const handlePaneClick = useCallback(
    (event: React.MouseEvent) => {
      if (isLocationSelectMode && reactFlow && onLocationSelect) {
        const flowPosition = reactFlow.screenToFlowPosition({
          x: event.clientX,
          y: event.clientY,
        });
        // Immediately confirm the location when clicking on the map
        onLocationSelect(flowPosition.x, flowPosition.y);
      }
    },
    [isLocationSelectMode, reactFlow, onLocationSelect]
  );

  const nodes = useMemo(() => {
    if (!map) return [];
    return buildNodes(
      map,
      selectedStationIds,
      isLocationSelectMode,
      locationSelectColor,
      handleNodeClick
    );
  }, [map, selectedStationIds, isLocationSelectMode, locationSelectColor, handleNodeClick]);

  const edges = useMemo(() => {
    if (!map) return [];
    return buildEdges(map);
  }, [map]);

  if (!map) {
    return (
      <div className="flex h-full w-full items-center justify-center">
        <div className="text-lg text-gray-500">Loading map...</div>
      </div>
    );
  }

  return (
    <div className="relative h-full w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onPaneClick={handlePaneClick}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.1}
        maxZoom={2}
        proOptions={{ hideAttribution: true }}
        className={clsx(
          isLocationSelectMode && "cursor-crosshair"
        )}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={20}
          size={1}
          color={scheme === "dark" ? "#444" : "#ccc"}
        />
      </ReactFlow>

      {/* Location select mode indicator */}
      {isLocationSelectMode && (
        <div
          className={clsx(
            "absolute left-4 top-4 rounded-lg px-4 py-2 shadow-lg",
            scheme === "dark"
              ? "bg-gray-800 text-white"
              : "bg-white text-gray-800"
          )}
        >
          <div className="flex items-center gap-2">
            <div
              className="h-3 w-3 animate-pulse rounded-full"
              style={{ backgroundColor: locationSelectColor || "#0088cc" }}
            />
            <span className="text-sm font-medium">
              Click on the map to select a location
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

type MetroMapCanvasProps = {
  className?: string;
  onLocationSelect?: (x: number, y: number) => void;
};

export function MetroMapCanvas({ className, onLocationSelect }: MetroMapCanvasProps) {
  return (
    <div className={clsx("h-full w-full", className)}>
      <ReactFlowProvider>
        <MetroMapCanvasContents onLocationSelect={onLocationSelect} />
      </ReactFlowProvider>
    </div>
  );
}
