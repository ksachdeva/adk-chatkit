export const CHATKIT_API_URL = "/metro-map/chatkit";
export const CHATKIT_API_DOMAIN_KEY = import.meta.env.VITE_CHATKIT_API_DOMAIN_KEY ?? "domain_pk_localhost_dev";

export const GREETING = "I'm here to help you explore and modify the metro map!";

export const STARTER_PROMPTS = [
  {
    label: "Add a new station",
    prompt: "Add a new station to the map",
    icon: "sparkle" as const,
  },
  {
    label: "Find a station",
    prompt: "Find a station on the map",
    icon: "document" as const,
  },
];

export const ENTITY_DEFINITION = {
  station: {
    kind: "tag" as const,
    label: "station",
    icon: "pin" as const,
    renderContent: (entity: { data?: Record<string, unknown> }) => {
      return (entity.data?.name ?? "Station") as string;
    },
    search: {
      enabled: true,
      placeholder: "Search stations...",
    },
  },
};

// OpenAI Sans font configuration
export const OPENAI_SANS_SOURCES = [
  {
    url: "https://cdn.openai.com/common/fonts/openai-sans/normal/400.woff2",
    format: "woff2",
    style: "normal",
    weight: 400,
  },
  {
    url: "https://cdn.openai.com/common/fonts/openai-sans/normal/500.woff2",
    format: "woff2",
    style: "normal",
    weight: 500,
  },
  {
    url: "https://cdn.openai.com/common/fonts/openai-sans/normal/600.woff2",
    format: "woff2",
    style: "normal",
    weight: 600,
  },
  {
    url: "https://cdn.openai.com/common/fonts/openai-sans/normal/700.woff2",
    format: "woff2",
    style: "normal",
    weight: 700,
  },
  {
    url: "https://cdn.openai.com/common/fonts/openai-sans/italic/400.woff2",
    format: "woff2",
    style: "italic",
    weight: 400,
  },
  {
    url: "https://cdn.openai.com/common/fonts/openai-sans/italic/500.woff2",
    format: "woff2",
    style: "italic",
    weight: 500,
  },
  {
    url: "https://cdn.openai.com/common/fonts/openai-sans/italic/600.woff2",
    format: "woff2",
    style: "italic",
    weight: 600,
  },
  {
    url: "https://cdn.openai.com/common/fonts/openai-sans/italic/700.woff2",
    format: "woff2",
    style: "italic",
    weight: 700,
  },
];
