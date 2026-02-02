import { ChatKit, useChatKit } from "@openai/chatkit-react";
import clsx from "clsx";
import { useCallback, useMemo, useRef } from "react";

import { useMetroMapStore } from "../../store/useMetroMapStore";
import {
  CHATKIT_API_URL,
  CHATKIT_API_DOMAIN_KEY,
  GREETING,
  STARTER_PROMPTS,
} from "../../lib/metro-map/config";
import { fetchMetroMap, type Station } from "../../lib/metro-map/map";

export type ChatKitInstance = ReturnType<typeof useChatKit>;

type ChatKitPanelProps = {
  onChatKitReady: (chatkit: ChatKitInstance) => void;
  className?: string;
};

export function ChatKitPanel({ onChatKitReady, className }: ChatKitPanelProps) {
  const chatkitRef = useRef<ChatKitInstance | null>(null);

  const theme = useMetroMapStore((state) => state.scheme);
  const threadId = useMetroMapStore((state) => state.threadId);
  const setThreadId = useMetroMapStore((state) => state.setThreadId);
  const map = useMetroMapStore((state) => state.map);
  const setMap = useMetroMapStore((state) => state.setMap);
  const focusStation = useMetroMapStore((state) => state.focusStation);
  const setInteractionMode = useMetroMapStore((state) => state.setInteractionMode);
  const setLocationSelectLineId = useMetroMapStore((state) => state.setLocationSelectLineId);
  const selectedStationIds = useMetroMapStore((state) => state.selectedStationIds);

  const customFetch = useMemo(() => {
    return async (input: RequestInfo | URL, init?: RequestInit) => {
      const headers = new Headers(init?.headers ?? {});
      if (threadId) {
        headers.set("X-Thread-Id", threadId);
      }
      return fetch(input, { ...init, headers });
    };
  }, [threadId]);

  // Handle client tool calls (get_selected_stations)
  const handleClientTool = useCallback(
    async (invocation: { name: string; params: Record<string, unknown> }): Promise<Record<string, unknown>> => {
      if (invocation.name === "get_selected_stations") {
        const selectedStations = selectedStationIds
          .map((id) => map?.stations[id])
          .filter((s): s is Station => s !== undefined)
          .map((s) => ({ id: s.id, name: s.name }));
        return { stations: selectedStations };
      }
      return {};
    },
    [selectedStationIds, map]
  );

  // Handle effects from server (location_select_mode, add_station)
  const handleEffect = useCallback(
    ({ name, data }: { name: string; data: Record<string, unknown> }) => {
      if (name === "location_select_mode") {
        const lineId = data?.line_id as string | undefined;
        if (lineId) {
          setInteractionMode("location_select");
          setLocationSelectLineId(lineId);
        } else {
          setInteractionMode("default");
          setLocationSelectLineId(null);
        }
      } else if (name === "add_station") {
        // Refetch the map to get the new station
        fetchMetroMap(threadId).then((updatedMap) => {
          setMap(updatedMap);
          // Focus on the new station if provided
          const stationId = data?.station_id as string | undefined;
          if (stationId) {
            focusStation(stationId);
          }
        });
      } else if (name === "remove_station" || name === "update_map") {
        // Refetch the map to get latest state
        fetchMetroMap(threadId).then((updatedMap) => {
          setMap(updatedMap);
        });
      }
    },
    [threadId, setMap, focusStation, setInteractionMode, setLocationSelectLineId]
  );

  const chatkit = useChatKit({
    api: {
      url: CHATKIT_API_URL,
      domainKey: CHATKIT_API_DOMAIN_KEY,
      fetch: customFetch,
    },
    theme: {
      density: "spacious",
      colorScheme: theme,
      color: {
        grayscale: { hue: 220, tint: 0, shade: theme === "dark" ? -1 : 0 },
        accent: { primary: "#0088cc", level: 1 },
      },
      radius: "round",
    },
    startScreen: {
      greeting: GREETING,
      prompts: STARTER_PROMPTS,
    },
    composer: {
      placeholder: threadId
        ? "Continue your metro map exploration..."
        : "Ask about the metro map...",
    },
    threadItemActions: {
      feedback: false,
    },
    onClientTool: handleClientTool,
    onEffect: handleEffect,
    onThreadChange: ({ threadId }) => setThreadId(threadId),
    onError: ({ error }) => {
      console.error("ChatKit error", error);
    },
    onReady: () => {
      onChatKitReady?.(chatkit);
    },
  });
  chatkitRef.current = chatkit;

  return (
    <div className={clsx("relative h-full w-full overflow-hidden", className)}>
      <ChatKit control={chatkit.control} className="block h-full w-full" />
    </div>
  );
}
