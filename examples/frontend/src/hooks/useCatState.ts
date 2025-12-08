import { useCallback, useEffect, useRef, useState } from "react";

import { CAT_STATE_API_URL } from "../lib/cat/config";
import type { CatStatePayload, CatSpeechPayload } from "../lib/cat/cat";
import { DEFAULT_CAT_STATE } from "../lib/cat/cat";

type SpeechState = (CatSpeechPayload & { id: number }) | null;

type CatStateHook = {
  cat: CatStatePayload;
  speech: SpeechState;
  flashMessage: string | null;
  refreshCat: (threadId: string | null) => Promise<void>;
};

const SPEECH_TIMEOUT_MS = 10_000;
const FLASH_TIMEOUT_MS = 10_000;

export function useCatState(threadId: string | null): CatStateHook {
  const [cat, setCat] = useState<CatStatePayload>(DEFAULT_CAT_STATE);
  const [speech, setSpeechState] = useState<SpeechState>(null);
  const [flashMessage, setFlashMessageState] = useState<string | null>(null);

  const speechTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const flashTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearSpeechTimer = useCallback(() => {
    if (speechTimerRef.current) {
      clearTimeout(speechTimerRef.current);
      speechTimerRef.current = null;
    }
  }, []);

  const clearFlashTimer = useCallback(() => {
    if (flashTimerRef.current) {
      clearTimeout(flashTimerRef.current);
      flashTimerRef.current = null;
    }
  }, []);

  const refreshCat = useCallback(
    async (id: string | null) => {
      if (!id) {
        setCat({
          ...DEFAULT_CAT_STATE,
          threadId: null,
          updatedAt: new Date().toISOString(),
        });
        return;
      }

      try {
        const response = await fetch(`${CAT_STATE_API_URL}?thread_id=${encodeURIComponent(id)}`, {
          headers: { Accept: "application/json" },
        });
        if (!response.ok) {
          throw new Error(`Failed to load cat state (${response.status})`);
        }
        const data = (await response.json()) as { cat?: CatStatePayload };
        if (data?.cat) {
          setCat((prev) => {
            return data.cat!;
          });
        }
      } catch (error) {
        console.error("Failed to fetch cat state", error);
      }
    },
    []
  );

  useEffect(() => {
    void refreshCat(threadId);
  }, [threadId, refreshCat]);

  useEffect(() => {
    return () => {
      clearSpeechTimer();
      clearFlashTimer();
    };
  }, [clearSpeechTimer, clearFlashTimer]);

  return {
    cat,
    speech,
    flashMessage,
    refreshCat,
  };
}
