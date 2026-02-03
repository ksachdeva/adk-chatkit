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
  id: string;
  name: string;
  summary: string;
  stations: Station[];
  lines: Line[];
};

const MAP_API_URL = "/metro-map/map";

// Scaling constants to match reference implementation
export const X_UNIT = 160;
export const Y_UNIT = 80;

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
  const data = (await response.json()) as { map?: MetroMap };
  if (!data.map) {
    throw new Error("Metro map payload missing in response.");
  }
  return data.map;
}

export async function updateMetroMap(
  map: MetroMap,
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
    body: JSON.stringify({ map }),
  });
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to update metro map: ${response.statusText} - ${errorText}`);
  }
  const data = (await response.json()) as { map?: MetroMap };
  if (!data.map) {
    throw new Error("Metro map payload missing in response.");
  }
  return data.map;
}
