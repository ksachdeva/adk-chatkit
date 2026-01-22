import type { ReactFlowInstance } from "@xyflow/react";
import { create } from "zustand";

import type { MetroMap } from "../lib/metro-map/map";

export type ColorScheme = "light" | "dark";
export type InteractionMode = "default" | "location_select";

const THEME_STORAGE_KEY = "metro-map-theme";

type MetroMapState = {
  scheme: ColorScheme;
  setScheme: (scheme: ColorScheme) => void;
  threadId: string | null;
  setThreadId: (threadId: string | null) => void;
  map: MetroMap | null;
  setMap: (map: MetroMap | null) => void;
  reactFlow: ReactFlowInstance | null;
  setReactFlow: (rf: ReactFlowInstance | null) => void;
  focusStation: (stationId: string) => void;
  locationSelectLineId: string | null;
  setLocationSelectLineId: (id: string | null) => void;
  selectedStationIds: string[];
  setSelectedStationIds: (ids: string[]) => void;
  interactionMode: InteractionMode;
  setInteractionMode: (mode: InteractionMode) => void;
};

function getInitialScheme(): ColorScheme {
  if (typeof window === "undefined") {
    return "light";
  }
  const stored = window.localStorage.getItem(THEME_STORAGE_KEY) as ColorScheme | null;
  if (stored === "light" || stored === "dark") {
    return stored;
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function syncSchemeWithDocument(scheme: ColorScheme) {
  if (typeof document === "undefined" || typeof window === "undefined") {
    return;
  }
  const root = document.documentElement;
  if (scheme === "dark") {
    root.classList.add("dark");
  } else {
    root.classList.remove("dark");
  }
  window.localStorage.setItem(THEME_STORAGE_KEY, scheme);
}

export const useMetroMapStore = create<MetroMapState>((set, get) => {
  const initialScheme = getInitialScheme();
  syncSchemeWithDocument(initialScheme);

  return {
    scheme: initialScheme,
    setScheme: (scheme) => {
      syncSchemeWithDocument(scheme);
      set({ scheme });
    },
    threadId: null,
    setThreadId: (threadId) => {
      set({ threadId });
    },
    map: null,
    setMap: (map) => {
      set({ map });
    },
    reactFlow: null,
    setReactFlow: (rf) => {
      set({ reactFlow: rf });
    },
    focusStation: (stationId) => {
      const rf = get().reactFlow;
      const map = get().map;
      if (!rf || !map) return;
      const station = map.stations[stationId];
      if (!station) return;
      rf.setCenter(station.x, station.y, { duration: 500, zoom: 1 });
    },
    locationSelectLineId: null,
    setLocationSelectLineId: (id) => {
      set({ locationSelectLineId: id });
    },
    selectedStationIds: [],
    setSelectedStationIds: (ids) => {
      set({ selectedStationIds: ids });
    },
    interactionMode: "default",
    setInteractionMode: (mode) => {
      set({ interactionMode: mode });
    },
  };
});
