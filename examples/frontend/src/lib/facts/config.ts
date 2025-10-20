import { StartScreenPrompt } from "@openai/chatkit";


export const CHATKIT_API_DOMAIN_KEY =
  import.meta.env.VITE_CHATKIT_API_DOMAIN_KEY ?? "domain_pk_localhost_dev";

export const FACTS_CHATKIT_API_URL = import.meta.env.VITE_FACTS_API_URL ?? "/facts/chatkit";

export const THEME_STORAGE_KEY = "chatkit-boilerplate-theme";

export const GREETING = "Welcome to the ChatKit Demo";

export const STARTER_PROMPTS: StartScreenPrompt[] = [
  {
    label: "What can you do?",
    prompt: "What can you do?",
    icon: "circle-question",
  },
  {
    label: "My name is Kaz",
    prompt: "My name is Kaz",
    icon: "book-open",
  },
  {
    label: "What's the weather in Paris?",
    prompt: "What's the weather in Paris?",
    icon: "search",
  },
  {
    label: "Change the theme to dark mode",
    prompt: "Change the theme to dark mode",
    icon: "sparkle",
  },
];

export const PLACEHOLDER_INPUT = "Share a fact about yourself";
