import { useCallback, useEffect, useRef, useState } from "react";
import confetti from "canvas-confetti";

import { CAT_STATE_API_URL } from "../lib/cat/config";
import type { CatStatePayload, CatSpeechPayload } from "../lib/cat/cat";
import { DEFAULT_CAT_STATE } from "../lib/cat/cat";

type SpeechState = (CatSpeechPayload & { id: number }) | null;

type CatStateHook = {
  cat: CatStatePayload;
  speech: SpeechState;
  flashMessage: string | null;
  refreshCat: (threadId: string | null) => Promise<void>;
  setSpeech: (speech: CatSpeechPayload | null) => void;
  setFlashMessage: (message: string | null) => void;
};

const SPEECH_TIMEOUT_MS = 10_000;
const FLASH_TIMEOUT_MS = 10_000;

function celebrateReveal() {
  confetti({
    particleCount: 50,
    spread: 100,
    origin: { y: 0.7 },
    zIndex: 1000,
    scalar: 0.9,
  });
}

function celebratePerfectStats() {
  const heart = confetti.shapeFromText({ text: "❤️", scalar: 2 });
  confetti({
    scalar: 2,
    particleCount: 10,
    flat: true,
    gravity: 0.5,
    spread: 120,
    origin: { y: 0.7 },
    zIndex: 1000,
    shapes: [heart],
  });
}

export function useCatState(threadId: string | null): CatStateHook {
  const [cat, setCat] = useState<CatStatePayload>(DEFAULT_CAT_STATE);
  const [speech, setSpeechState] = useState<SpeechState>(null);
  const [flashMessage, setFlashMessageState] = useState<string | null>(null);
  const prevCatRef = useRef<CatStatePayload>(DEFAULT_CAT_STATE);

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
        const resetCat = {
          ...DEFAULT_CAT_STATE,
          threadId: null,
          updatedAt: new Date().toISOString(),
        };
        prevCatRef.current = resetCat;
        setCat(resetCat);
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
          const newCat = data.cat;
          const prev = prevCatRef.current;

          // Celebrate when cat gets named
          if (prev.name === "Unnamed Cat" && newCat.name !== prev.name) {
            celebrateReveal();
          }

          // Celebrate when all stats reach perfect (10/10/10)
          if (
            (prev.energy < 10 || prev.happiness < 10 || prev.cleanliness < 10) &&
            newCat.energy === 10 &&
            newCat.happiness === 10 &&
            newCat.cleanliness === 10
          ) {
            celebratePerfectStats();
          }

          prevCatRef.current = newCat;
          setCat(newCat);
        }
      } catch (error) {
        console.error("Failed to fetch cat state", error);
      }
    },
    []
  );

  const setSpeech = useCallback(
    (speechPayload: CatSpeechPayload | null) => {
      clearSpeechTimer();
      if (speechPayload) {
        const id = Date.now();
        setSpeechState({ ...speechPayload, id });
        speechTimerRef.current = setTimeout(() => {
          setSpeechState(null);
        }, SPEECH_TIMEOUT_MS);
      } else {
        setSpeechState(null);
      }
    },
    [clearSpeechTimer]
  );

  const setFlashMessage = useCallback(
    (message: string | null) => {
      clearFlashTimer();
      if (message) {
        setFlashMessageState(message);
        flashTimerRef.current = setTimeout(() => {
          setFlashMessageState(null);
        }, FLASH_TIMEOUT_MS);
      } else {
        setFlashMessageState(null);
      }
    },
    [clearFlashTimer]
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
    setSpeech,
    setFlashMessage,
  };
}
