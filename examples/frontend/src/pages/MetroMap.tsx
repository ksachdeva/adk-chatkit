import clsx from "clsx";
import { useCallback, useEffect, useRef } from "react";

import { ChatKitPanel } from "../components/metro-map/ChatKitPanel";
import type { ChatKitInstance } from "../components/metro-map/ChatKitPanel";
import { MapPanel } from "../components/metro-map/MapPanel";
import { ThemeToggle } from "../components/metro-map/ThemeToggle";
import { useMetroMapStore } from "../store/useMetroMapStore";
import { fetchMetroMap } from "../lib/metro-map/map";
import "../components/metro-map/MetroMapCanvas.css";

export default function MetroMapPage() {
  const chatkitRef = useRef<ChatKitInstance | null>(null);
  const scheme = useMetroMapStore((state) => state.scheme);
  const setMap = useMetroMapStore((state) => state.setMap);
  const threadId = useMetroMapStore((state) => state.threadId);

  // Fetch initial map data
  useEffect(() => {
    fetchMetroMap(threadId)
      .then((map) => {
        setMap(map);
      })
      .catch((error) => {
        console.error("Failed to fetch metro map:", error);
      });
  }, [threadId, setMap]);

  const handleChatKitReady = useCallback((chatkit: ChatKitInstance) => {
    chatkitRef.current = chatkit;
  }, []);

  const containerClass = clsx(
    "h-screen flex flex-col transition-colors duration-300",
    scheme === "dark" ? "bg-gray-900 text-gray-100" : "bg-gray-100 text-gray-900"
  );

  const headerClass = clsx(
    "sticky top-0 z-30 w-full border-b shadow-sm",
    scheme === "dark"
      ? "border-gray-700 bg-gray-800"
      : "border-gray-200 bg-white"
  );

  return (
    <div className={containerClass}>
      {/* Header */}
      <header className={headerClass}>
        <div className="relative flex w-full items-center justify-between px-6 py-4">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-semibold tracking-tight">
              🚇 Metro Map
            </h1>
            <p
              className={clsx(
                "text-sm",
                scheme === "dark" ? "text-gray-400" : "text-gray-600"
              )}
            >
              Explore and modify the metro map with AI
            </p>
          </div>
          <ThemeToggle />
        </div>
      </header>

      {/* Main content: Map (70%) | Chat (30%) */}
      <div className="flex flex-1 min-h-0 flex-col md:flex-row">
        {/* Map Panel - 70% on desktop */}
        <div
          className={clsx(
            "flex flex-1 min-h-[400px] flex-col border-b md:basis-[70%] md:min-h-0 md:border-b-0 md:border-r",
            scheme === "dark"
              ? "border-gray-700 bg-gray-900"
              : "border-gray-200 bg-white"
          )}
        >
          <MapPanel className="flex-1" />
        </div>

        {/* Chat Panel - 30% on desktop */}
        <div
          className={clsx(
            "flex basis-full min-h-[400px] flex-col md:basis-[30%] md:min-h-0",
            scheme === "dark" ? "bg-gray-900" : "bg-white"
          )}
        >
          <ChatKitPanel
            className="flex-1"
            onChatKitReady={handleChatKitReady}
          />
        </div>
      </div>
    </div>
  );
}
