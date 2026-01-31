import { create } from "zustand";

export type ColorScheme = "light" | "dark";

const THEME_STORAGE_KEY = "news-theme";

type NewsState = {
  scheme: ColorScheme;
  setScheme: (scheme: ColorScheme) => void;
  threadId: string | null;
  setThreadId: (threadId: string | null) => void;
  articleId: string | null;
  setArticleId: (articleId: string | null) => void;
};

function getInitialScheme(): ColorScheme {
  if (typeof window === "undefined") {
    return "light";
  }
  const stored = window.localStorage.getItem(THEME_STORAGE_KEY) as ColorScheme | null;
  if (stored === "light" || stored === "dark") {
    return stored;
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function syncSchemeWithDocument(scheme: ColorScheme) {
  if (typeof document === "undefined" || typeof window === "undefined") {
    return;
  }
  const root = document.documentElement;
  if (scheme === "dark") {
    root.classList.add("dark");
  } else {
    root.classList.remove("dark");
  }
  window.localStorage.setItem(THEME_STORAGE_KEY, scheme);
}

export const useNewsStore = create<NewsState>((set) => {
  const initialScheme = getInitialScheme();
  syncSchemeWithDocument(initialScheme);

  return {
    scheme: initialScheme,
    setScheme: (scheme) => {
      syncSchemeWithDocument(scheme);
      set({ scheme });
    },
    threadId: null,
    setThreadId: (threadId) => {
      set({ threadId });
    },
    articleId: null,
    setArticleId: (articleId) => {
      set({ articleId });
    },
  };
});
