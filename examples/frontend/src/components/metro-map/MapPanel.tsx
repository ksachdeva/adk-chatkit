import clsx from "clsx";
import { useCallback, useState } from "react";
import ReactModal from "react-modal";

import { useMetroMapStore } from "../../store/useMetroMapStore";
import { MetroMapCanvas } from "./MetroMapCanvas";
import { updateMetroMap, type Line } from "../../lib/metro-map/map";

type MapPanelProps = {
  className?: string;
};

export function MapPanel({ className }: MapPanelProps) {
  const scheme = useMetroMapStore((state) => state.scheme);
  const map = useMetroMapStore((state) => state.map);
  const setMap = useMetroMapStore((state) => state.setMap);
  const threadId = useMetroMapStore((state) => state.threadId);
  const interactionMode = useMetroMapStore((state) => state.interactionMode);
  const setInteractionMode = useMetroMapStore((state) => state.setInteractionMode);
  const locationSelectLineId = useMetroMapStore((state) => state.locationSelectLineId);
  const setLocationSelectLineId = useMetroMapStore((state) => state.setLocationSelectLineId);

  const [isAddStationModalOpen, setIsAddStationModalOpen] = useState(false);
  const [addStationForm, setAddStationForm] = useState({
    name: "",
    lineId: "",
    x: 0,
    y: 0,
  });
  const [pendingLocation, setPendingLocation] = useState<{ x: number; y: number } | null>(null);

  const lines: Line[] = map ? Object.values(map.lines) : [];

  const handleOpenAddStationModal = useCallback(() => {
    if (lines.length === 0) {
      alert("No lines available. Create a line first.");
      return;
    }
    setAddStationForm((prev) => ({
      ...prev,
      lineId: lines[0]?.id || "",
    }));
    setIsAddStationModalOpen(true);
  }, [lines]);

  const handleStartLocationSelect = useCallback(() => {
    if (!addStationForm.lineId) {
      alert("Please select a line first");
      return;
    }
    setIsAddStationModalOpen(false);
    setInteractionMode("location_select");
    setLocationSelectLineId(addStationForm.lineId);
  }, [addStationForm.lineId, setInteractionMode, setLocationSelectLineId]);

  const handleLocationSelect = useCallback(
    (x: number, y: number) => {
      setPendingLocation({ x, y });
      setAddStationForm((prev) => ({ ...prev, x, y }));
      setInteractionMode("default");
      setLocationSelectLineId(null);
      setIsAddStationModalOpen(true);
    },
    [setInteractionMode, setLocationSelectLineId]
  );

  const handleAddStation = useCallback(async () => {
    if (!addStationForm.name.trim()) {
      alert("Please enter a station name");
      return;
    }
    if (!addStationForm.lineId) {
      alert("Please select a line");
      return;
    }

    const stationId = `station-${Date.now()}`;
    const newStation = {
      id: stationId,
      name: addStationForm.name.trim(),
      x: addStationForm.x,
      y: addStationForm.y,
      lines: [addStationForm.lineId],
      visible: true,
    };

    try {
      // Build the update payload
      const currentStations = map?.stations || {};
      const currentLines = map?.lines || {};
      const targetLine = currentLines[addStationForm.lineId];

      const updatedMap = await updateMetroMap(
        {
          stations: {
            ...currentStations,
            [stationId]: newStation,
          },
          lines: {
            ...currentLines,
            [addStationForm.lineId]: {
              ...targetLine,
              stations: [...(targetLine?.stations || []), stationId],
            },
          },
        },
        threadId
      );

      setMap(updatedMap);
      setIsAddStationModalOpen(false);
      setAddStationForm({ name: "", lineId: lines[0]?.id || "", x: 0, y: 0 });
      setPendingLocation(null);
    } catch (error) {
      console.error("Failed to add station:", error);
      alert("Failed to add station. Please try again.");
    }
  }, [addStationForm, map, threadId, setMap, lines]);

  const handleCloseModal = useCallback(() => {
    setIsAddStationModalOpen(false);
    setPendingLocation(null);
    setAddStationForm({ name: "", lineId: lines[0]?.id || "", x: 0, y: 0 });
  }, [lines]);

  const modalStyles = {
    overlay: {
      backgroundColor: scheme === "dark" ? "rgba(0, 0, 0, 0.75)" : "rgba(0, 0, 0, 0.5)",
      zIndex: 1000,
    },
    content: {
      top: "50%",
      left: "50%",
      right: "auto",
      bottom: "auto",
      transform: "translate(-50%, -50%)",
      padding: 0,
      border: "none",
      borderRadius: "12px",
      maxWidth: "400px",
      width: "90%",
      backgroundColor: scheme === "dark" ? "#1f2937" : "#ffffff",
    },
  };

  return (
    <div className={clsx("relative flex h-full w-full flex-col", className)}>
      {/* Toolbar */}
      <div
        className={clsx(
          "flex items-center gap-2 border-b px-4 py-2",
          scheme === "dark"
            ? "border-gray-700 bg-gray-800"
            : "border-gray-200 bg-gray-50"
        )}
      >
        <button
          onClick={handleOpenAddStationModal}
          className={clsx(
            "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
            scheme === "dark"
              ? "bg-blue-600 text-white hover:bg-blue-500"
              : "bg-blue-500 text-white hover:bg-blue-600"
          )}
        >
          <span>+</span>
          <span>Add Station</span>
        </button>

        {interactionMode === "location_select" && (
          <button
            onClick={() => {
              setInteractionMode("default");
              setLocationSelectLineId(null);
            }}
            className={clsx(
              "rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
              scheme === "dark"
                ? "bg-gray-700 text-gray-200 hover:bg-gray-600"
                : "bg-gray-200 text-gray-700 hover:bg-gray-300"
            )}
          >
            Cancel Selection
          </button>
        )}
      </div>

      {/* Map canvas */}
      <div className="flex-1">
        <MetroMapCanvas onLocationSelect={handleLocationSelect} />
      </div>

      {/* Add Station Modal */}
      <ReactModal
        isOpen={isAddStationModalOpen}
        onRequestClose={handleCloseModal}
        style={modalStyles}
        ariaHideApp={false}
      >
        <div
          className={clsx(
            "p-6",
            scheme === "dark" ? "text-gray-100" : "text-gray-900"
          )}
        >
          <h2 className="mb-4 text-lg font-semibold">Add New Station</h2>

          <div className="space-y-4">
            {/* Station name */}
            <div>
              <label className="mb-1 block text-sm font-medium">
                Station Name
              </label>
              <input
                type="text"
                value={addStationForm.name}
                onChange={(e) =>
                  setAddStationForm((prev) => ({ ...prev, name: e.target.value }))
                }
                placeholder="Enter station name"
                className={clsx(
                  "w-full rounded-lg border px-3 py-2 text-sm",
                  scheme === "dark"
                    ? "border-gray-600 bg-gray-700 text-white placeholder-gray-400"
                    : "border-gray-300 bg-white text-gray-900 placeholder-gray-500"
                )}
              />
            </div>

            {/* Line selection */}
            <div>
              <label className="mb-1 block text-sm font-medium">Line</label>
              <select
                value={addStationForm.lineId}
                onChange={(e) =>
                  setAddStationForm((prev) => ({ ...prev, lineId: e.target.value }))
                }
                className={clsx(
                  "w-full rounded-lg border px-3 py-2 text-sm",
                  scheme === "dark"
                    ? "border-gray-600 bg-gray-700 text-white"
                    : "border-gray-300 bg-white text-gray-900"
                )}
              >
                {lines.map((line) => (
                  <option key={line.id} value={line.id}>
                    {line.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Location */}
            <div>
              <label className="mb-1 block text-sm font-medium">Location</label>
              {pendingLocation ? (
                <div
                  className={clsx(
                    "flex items-center gap-2 rounded-lg border px-3 py-2 text-sm",
                    scheme === "dark"
                      ? "border-gray-600 bg-gray-700"
                      : "border-gray-300 bg-gray-100"
                  )}
                >
                  <span>
                    X: {Math.round(pendingLocation.x)}, Y:{" "}
                    {Math.round(pendingLocation.y)}
                  </span>
                  <button
                    onClick={handleStartLocationSelect}
                    className="ml-auto text-blue-500 hover:text-blue-600"
                  >
                    Change
                  </button>
                </div>
              ) : (
                <button
                  onClick={handleStartLocationSelect}
                  className={clsx(
                    "w-full rounded-lg border-2 border-dashed px-3 py-3 text-sm transition-colors",
                    scheme === "dark"
                      ? "border-gray-600 text-gray-400 hover:border-gray-500 hover:text-gray-300"
                      : "border-gray-300 text-gray-500 hover:border-gray-400 hover:text-gray-600"
                  )}
                >
                  Click to select location on map
                </button>
              )}
            </div>
          </div>

          {/* Actions */}
          <div className="mt-6 flex justify-end gap-2">
            <button
              onClick={handleCloseModal}
              className={clsx(
                "rounded-lg px-4 py-2 text-sm font-medium transition-colors",
                scheme === "dark"
                  ? "bg-gray-700 text-gray-200 hover:bg-gray-600"
                  : "bg-gray-200 text-gray-700 hover:bg-gray-300"
              )}
            >
              Cancel
            </button>
            <button
              onClick={handleAddStation}
              disabled={!addStationForm.name.trim() || !pendingLocation}
              className={clsx(
                "rounded-lg px-4 py-2 text-sm font-medium transition-colors",
                !addStationForm.name.trim() || !pendingLocation
                  ? "cursor-not-allowed bg-gray-400 text-gray-200"
                  : scheme === "dark"
                  ? "bg-blue-600 text-white hover:bg-blue-500"
                  : "bg-blue-500 text-white hover:bg-blue-600"
              )}
            >
              Add Station
            </button>
          </div>
        </div>
      </ReactModal>
    </div>
  );
}
