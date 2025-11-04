import { StartScreenPrompt } from "@openai/chatkit";

export const THEME_STORAGE_KEY = "adk-chatkit-theme";

const GALLERY_API_BASE =
  import.meta.env.VITE_SUPPORT_API_BASE ?? "/widgets";

export const WIDGET_CHATKIT_API_DOMAIN_KEY =
  import.meta.env.VITE_WIDGET_CHATKIT_API_DOMAIN_KEY ?? "domain_pk_localhost_dev";

export const WIDGET_CHATKIT_API_URL =
  import.meta.env.VITE_WIDGET_CHATKIT_API_URL ??
  `${GALLERY_API_BASE}/chatkit`;

export const WIDGET_CUSTOMER_URL =
  import.meta.env.VITE_WIDGET_CUSTOMER_URL ??
  `${GALLERY_API_BASE}/customer`;

export const WIDGET_GREETING =
  import.meta.env.VITE_WIDGET_GREETING ??
  "The Widgets Gallery. How can I assist you today?";

export const WIDGET_STARTER_PROMPTS: StartScreenPrompt[] = [
  {
    label: "Email Widget",
    prompt: "Craft and preview an email before sending",
    icon: "lightbulb",
  },
  {
    label: "Calendar Widget",
    prompt: "Add events to your calendar",
    icon: "sparkle",
  },
  {
    label: "Tasks Widget",
    prompt: "Manage your tasks and to-dos",
    icon: "compass",
  },
];
