import { ChatKit, useChatKit } from "@openai/chatkit-react";
import type { ColorScheme } from "../../hooks/useColorScheme";
import {
  WIDGET_CHATKIT_API_DOMAIN_KEY,
  WIDGET_CHATKIT_API_URL,
  WIDGET_GREETING,
  WIDGET_STARTER_PROMPTS,
} from "../../lib/widget-gallery/config";

type ChatKitPanelProps = {
  theme: ColorScheme;
  onThreadChange: (threadId: string | null) => void;
  onResponseCompleted: () => void;
};

export function ChatKitPanel({
  theme,
  onThreadChange,
  onResponseCompleted,
}: ChatKitPanelProps) {

  const chatkit = useChatKit({
    api: {
      url: WIDGET_CHATKIT_API_URL,
      domainKey: WIDGET_CHATKIT_API_DOMAIN_KEY,
    },
    theme: {
      colorScheme: theme,
      color: {
        grayscale: {
          hue: 220,
          tint: 6,
          shade: theme === "dark" ? -1 : -4,
        },
        accent: {
          primary: theme === "dark" ? "#f8fafc" : "#0f172a",
          level: 1,
        },
      },
      radius: "round",
    },
    startScreen: {
      greeting: WIDGET_GREETING,
      prompts: WIDGET_STARTER_PROMPTS,
    },
    composer: {
      placeholder: "Explore various widgets",
    },
    threadItemActions: {
      feedback: false,
    },
    onResponseEnd: () => {
      onResponseCompleted();
    },
    onThreadChange: ({ threadId }) => {
      onThreadChange(threadId ?? null);
    },
    onError: ({ error }) => {
      // ChatKit displays surfaced errors; we keep logging for debugging.
      console.error("ChatKit error", error);
    },
  });

  return (
    <div className="relative h-full w-full overflow-hidden border border-slate-200/60 bg-white shadow-card dark:border-slate-800/70 dark:bg-slate-900">
      <ChatKit control={chatkit.control} className="block h-full w-full" />
    </div>
  );
}
