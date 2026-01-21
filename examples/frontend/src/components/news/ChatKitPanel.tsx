import { ChatKit, useChatKit, Widgets, type Entity } from "@openai/chatkit-react";
import clsx from "clsx";
import { useCallback, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useNewsStore } from "../../store/useNewsStore";

export type ChatKit = ReturnType<typeof useChatKit>;

const CHATKIT_API_URL = "/news/chatkit";
const CHATKIT_API_DOMAIN_KEY = import.meta.env.VITE_CHATKIT_API_DOMAIN_KEY ?? "domain_pk_localhost_dev";

const GREETING = "I'm here to help you find the latest news from Foxhollow";

const STARTER_PROMPTS = [
  {
    label: "Browse trending stories",
    prompt: "What's trending right now?",
    icon: "globe" as const,
  },
  {
    label: "Read some gossip",
    prompt: "Any small-town drama lately?",
    icon: "sparkle" as const,
  },
  {
    label: "Get public works updates",
    prompt: "What's the latest on public infrastructure projects?",
    icon: "lightbulb" as const,
  },
  {
    label: "Summarize this page",
    prompt: "Give me a summary of this page.",
    icon: "document" as const,
  },
];

const TOOL_CHOICES = [
  {
    id: "delegate_to_event_finder",
    label: "Event finder",
    icon: "calendar" as const,
    placeholderOverride: "Anything happening this weekend?",
  },
  {
    id: "delegate_to_puzzle_keeper",
    label: "Coffee break puzzle",
    shortLabel: "Puzzle",
    icon: "atom" as const,
    placeholderOverride: "Give me a puzzle to solve",
  },
];

const LORA_SOURCES = [
  {
    url: "https://fonts.gstatic.com/s/lora/v35/0QI6MX1D_JOuGQbT0gvTJPa787weuxJBkq0.woff2",
    format: "woff2",
    style: "normal",
    weight: 400,
  },
  {
    url: "https://fonts.gstatic.com/s/lora/v35/0QI8MX1D_JOuMw_hLdO6T2wV9K_Gzux5T-RY.woff2",
    format: "woff2",
    style: "italic",
    weight: 400,
  },
  {
    url: "https://fonts.gstatic.com/s/lora/v35/0QI6MX1D_JOuGQbT0gvTJPa787z-uBJBkq0.woff2",
    format: "woff2",
    style: "normal",
    weight: 600,
  },
];

type ChatKitPanelProps = {
  onChatKitReady: (chatkit: ChatKit) => void;
  className?: string;
};

export function ChatKitPanel({ onChatKitReady, className }: ChatKitPanelProps) {
  const chatkitRef = useRef<ReturnType<typeof useChatKit> | null>(null);
  const [lastActionedArticle, setLastActionedArticle] = useState<string | null>(null);
  const navigate = useNavigate();

  const theme = useNewsStore((state) => state.scheme);
  const threadId = useNewsStore((state) => state.threadId);
  const setThreadId = useNewsStore((state) => state.setThreadId);
  const articleId = useNewsStore((state) => state.articleId);

  const customFetch = useMemo(() => {
    return async (input: RequestInfo | URL, init?: RequestInit) => {
      const headers = new Headers(init?.headers ?? {});
      const currentArticleId = articleId ?? "featured";
      if (currentArticleId) {
        headers.set("article-id", currentArticleId);
      } else {
        headers.delete("article-id");
      }
      return fetch(input, {
        ...init,
        headers,
      });
    };
  }, [articleId]);

  const handleWidgetAction = useCallback(
    async (
      action: { type: string; payload?: Record<string, unknown> },
      widgetItem: { id: string; widget: Widgets.Card | Widgets.ListView }
    ) => {
      switch (action.type) {
        case "open_article": {
          const id = action.payload?.id;
          if (typeof id === "string" && id) {
            navigate(`/news-guide/${id}`);
            const chatkit = chatkitRef.current;

            if (chatkit) {
              if (id !== lastActionedArticle) {
                await chatkit.sendCustomAction(action, widgetItem.id);
                setLastActionedArticle(id);
              }
            }
          }
          break;
        }
      }
    },
    [navigate, lastActionedArticle]
  );

  const handleEntityClick = useCallback(
    (entity: Entity) => {
      const rawId = entity.data?.["article_id"];
      const articleId = typeof rawId === "string" ? rawId.trim() : "";
      if (articleId) {
        navigate(`/news-guide/${articleId}`);
      }
    },
    [navigate]
  );

  const chatkit = useChatKit({
    api: { url: CHATKIT_API_URL, domainKey: CHATKIT_API_DOMAIN_KEY, fetch: customFetch },
    theme: {
      density: "spacious",
      colorScheme: theme,
      color: {
        grayscale: {
          hue: 0,
          tint: 0,
          shade: theme === "dark" ? -1 : 0,
        },
        accent: {
          primary: "#ff5f42",
          level: 1,
        },
      },
      typography: {
        fontFamily: "Lora, serif",
      },
      radius: "sharp",
    },
    startScreen: {
      greeting: GREETING,
      prompts: STARTER_PROMPTS,
    },
    composer: {
      placeholder: threadId ? "Ask for related stories" : "Any small-town drama this week?",
      tools: TOOL_CHOICES,
    },
    entities: {
      onClick: handleEntityClick,
    },
    threadItemActions: {
      feedback: false,
    },
    widgets: {
      onAction: handleWidgetAction,
    },
    onThreadChange: ({ threadId }) => setThreadId(threadId),
    onError: ({ error }) => {
      console.error("ChatKit error", error);
    },
    onReady: () => {
      onChatKitReady?.(chatkit);
    },
  });
  chatkitRef.current = chatkit;

  return (
    <div className={clsx("relative h-full w-full overflow-hidden", className)}>
      <ChatKit control={chatkit.control} className="block h-full w-full" />
    </div>
  );
}
