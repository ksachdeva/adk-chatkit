export type Station = {
  id: string;
  name: string;
  description?: string;
  x: number;
  y: number;
  lines: string[];
  visible?: boolean;
};

export type Line = {
  id: string;
  name: string;
  color: string;
  stations: string[];
};

export type MetroMap = {
  stations: Record<string, Station>;
  lines: Record<string, Line>;
};

// Backend response types (arrays)
type BackendStation = Station;
type BackendLine = Line;
type BackendMapResponse = {
  map: {
    id: string;
    name: string;
    summary: string;
    stations: BackendStation[];
    lines: BackendLine[];
  };
};

const MAP_API_URL = "/metro-map/map";

// Scale factor to convert grid coordinates to pixel positions
const GRID_SCALE = 150;
const GRID_OFFSET_X = 300;
const GRID_OFFSET_Y = 400;

function transformBackendResponse(response: BackendMapResponse): MetroMap {
  const stationsRecord: Record<string, Station> = {};
  for (const station of response.map.stations) {
    stationsRecord[station.id] = {
      ...station,
      // Scale grid coordinates to pixel positions
      x: station.x * GRID_SCALE + GRID_OFFSET_X,
      y: station.y * GRID_SCALE + GRID_OFFSET_Y,
      visible: true,
    };
  }

  const linesRecord: Record<string, Line> = {};
  for (const line of response.map.lines) {
    linesRecord[line.id] = line;
  }

  return { stations: stationsRecord, lines: linesRecord };
}

export async function fetchMetroMap(threadId?: string | null): Promise<MetroMap> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (threadId) {
    headers["X-Thread-Id"] = threadId;
  }

  const response = await fetch(MAP_API_URL, {
    method: "GET",
    headers,
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch metro map: ${response.statusText}`);
  }
  const data: BackendMapResponse = await response.json();
  return transformBackendResponse(data);
}

export async function updateMetroMap(
  update: Partial<MetroMap>,
  threadId?: string | null
): Promise<MetroMap> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (threadId) {
    headers["X-Thread-Id"] = threadId;
  }

  const response = await fetch(MAP_API_URL, {
    method: "POST",
    headers,
    body: JSON.stringify(update),
  });
  if (!response.ok) {
    throw new Error(`Failed to update metro map: ${response.statusText}`);
  }
  return response.json();
}
