import { ChatKit, useChatKit } from "@openai/chatkit-react";
import type { Widgets } from "@openai/chatkit";
import clsx from "clsx";
import { useCallback, useEffect, useRef } from "react";
import type { ColorScheme } from "../../hooks/useColorScheme";

import {
  CAT_CHATKIT_API_DOMAIN_KEY,
  CAT_CHATKIT_API_URL,
  CAT_GREETING,
  CAT_STARTER_PROMPTS,
  getPlaceholder,
} from "../../lib/cat/config";

type ChatKitPanelProps = {
  theme: ColorScheme;
  onThreadChange: (threadId: string | null) => void;
  onResponseCompleted: () => void;
  threadId: string | null;
  catName: string;
  refreshCat: (threadId: string | null) => Promise<void>;
  onChatKitReady?: (chatkit: ChatKit) => void;
  className?: string;
};

export type ChatKit = ReturnType<typeof useChatKit>;

export function ChatKitPanel({
  theme,
  onThreadChange,
  onResponseCompleted,
  threadId,
  catName,
  refreshCat,
  onChatKitReady,
  className,
}: ChatKitPanelProps) {
  const chatkitRef = useRef<ReturnType<typeof useChatKit> | null>(null);

  const handleWidgetAction = useCallback(
    async (
      action: { type: string; payload?: Record<string, unknown> },
      widgetItem: { id: string; widget: Widgets.Card | Widgets.ListView }
    ) => {
      const chatkit = chatkitRef.current;
      if (!chatkit) {
        return;
      }
      // When the user clicks "Suggest more names", the client action handler simply
      // sends a user message using a chatkit command.
      if (action.type === "cats.more_names") {
        await chatkit.sendUserMessage({ text: "More name suggestions, please" });
        return;
      }
      // This is a more complex client action handler that:
      // - Invokes the server action handler
      // - Then fetches the latest post-server-action cat status
      if (action.type === "cats.select_name") {
        if (!threadId) {
          console.warn("Ignoring name selection without an active thread.");
          return;
        }
        // Send the server action.
        await chatkit.sendCustomAction(action, widgetItem.id);
        // Then fetch the latest cat status so that we can reflect the update client-side.
        await refreshCat(threadId);
        return;
      }
    },
    [refreshCat, threadId]
  );

  const chatkit = useChatKit({
    api: { url: CAT_CHATKIT_API_URL, domainKey: CAT_CHATKIT_API_DOMAIN_KEY },
    theme: {
      density: "spacious",
      colorScheme: theme,
      color: {
        grayscale: {
          hue: 220,
          tint: 6,
          shade: theme === "dark" ? -1 : -4,
        },
        accent: {
          primary: theme === "dark" ? "#f1f5f9" : "#0f172a",
          level: 1,
        },
      },
      radius: "round",
    },
    startScreen: {
      greeting: CAT_GREETING,
      prompts: CAT_STARTER_PROMPTS,
    },
    composer: {
      placeholder: getPlaceholder(catName),
    },
    threadItemActions: {
      feedback: false,
    },
    widgets: {
      onAction: handleWidgetAction,
    },
    onThreadChange: ({ threadId }) => onThreadChange(threadId ?? null),
    onError: ({ error }) => {
      // ChatKit handles displaying the error to the user
      console.error("ChatKit error", error);
    },
    onResponseEnd: () => {
      onResponseCompleted();
      // Refresh cat state after response completes
      if (threadId) {
        void refreshCat(threadId);
      }
    },
  });
  chatkitRef.current = chatkit;

  useEffect(() => {
    if (chatkit && onChatKitReady) {
      onChatKitReady(chatkit);
    }
  }, [chatkit, onChatKitReady]);

  return (
    <div className={clsx("relative h-full w-full overflow-hidden", className)}>
      <ChatKit control={chatkit.control} className="block h-full w-full" />
    </div>
  );
}
