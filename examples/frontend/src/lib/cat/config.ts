import { StartScreenPrompt } from "@openai/chatkit";
import { DEFAULT_CAT_STATE } from "./cat";

export const THEME_STORAGE_KEY = "adk-chatkit-theme";

const CAT_API_BASE = import.meta.env.VITE_CAT_API_BASE ?? "/cat";

export const CAT_CHATKIT_API_DOMAIN_KEY =
  import.meta.env.VITE_CAT_CHATKIT_API_DOMAIN_KEY ?? "domain_pk_localhost_dev";

export const CAT_CHATKIT_API_URL =
  import.meta.env.VITE_CAT_CHATKIT_API_URL ?? `${CAT_API_BASE}/chatkit`;

export const CAT_STATE_API_URL =
  import.meta.env.VITE_CAT_STATE_API_URL ?? `${CAT_API_BASE}/cat`;

export const CAT_GREETING =
  import.meta.env.VITE_CAT_GREETING ?? "Welcome to the cozy cat lounge";

export const CAT_STARTER_PROMPTS: StartScreenPrompt[] = [
  {
    label: "Name ideas",
    prompt: "Could you suggest some fun names for the cat?",
    icon: "book-open",
  },
  {
    label: "Check on the cat",
    prompt: "How is the cat doing today?",
    icon: "circle-question",
  },
  {
    label: "Feed time",
    prompt: "Please feed the cat something tasty.",
    icon: "sparkle",
  },
  {
    label: "Play time",
    prompt: "Please play with the cat using a fun toy.",
    icon: "confetti",
  },
  {
    label: "Profile card",
    prompt: "Can you show me the cat's profile card?",
    icon: "square-text",
  },
];

export const getPlaceholder = (catName: string | null) => {
  return catName === DEFAULT_CAT_STATE.name
    ? "Ask how the cat feels or what it needs"
    : `${catName}, what would you like to do?`;
};
