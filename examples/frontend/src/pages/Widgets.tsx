import { useCallback, useState } from "react";
import clsx from "clsx";

import { ChatKitPanel } from "../components/widget-gallery/ChatKitPanel";
import { ThemeToggle } from "../components/ThemeToggle";
import type { ColorScheme } from "../hooks/useColorScheme";
import { useColorScheme } from "../hooks/useColorScheme";

export default function WidgetGallery() {
    const [threadId, setThreadId] = useState<string | null>(null);

    const { scheme, setScheme } = useColorScheme();

    const handleThemeChange = useCallback(
        (value: ColorScheme) => {
            setScheme(value);
        },
        [setScheme],
    );

    const containerClass = clsx(
        "min-h-screen bg-gradient-to-br transition-colors duration-300",
        scheme === "dark"
            ? "from-slate-950 via-slate-950 to-slate-900 text-slate-100"
            : "from-slate-100 via-white to-slate-200 text-slate-900",
    );

    const handleThreadChange = useCallback((nextThreadId: string | null) => {
        setThreadId(nextThreadId);
    }, []);

    const handleResponseCompleted = useCallback(() => {

    }, []);

    return (
        <div className={containerClass}>
            <div className="mx-auto flex min-h-screen w-full max-w-6xl flex-col gap-8 px-6 py-8 lg:h-screen lg:max-h-screen lg:py-10">
                <header className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
                    <div className="space-y-3">
                        <p className="text-sm uppercase tracking-[0.2em] text-slate-500 dark:text-slate-400">
                            OpenAI ChatKit Widgets Gallery
                        </p>
                        <h1 className="text-3xl font-semibold sm:text-4xl">
                            Explore various ChatKit widgets
                        </h1>
                        <p className="max-w-3xl text-sm text-slate-600 dark:text-slate-300">
                            Chat with the agent on the left. The right panel shows various actions
                            and events triggered from the widgets.
                        </p>
                    </div>
                    <ThemeToggle value={scheme} onChange={handleThemeChange} />
                </header>

                <div className="grid flex-1 grid-cols-1 gap-8 lg:h-[calc(100vh-260px)] lg:grid-cols-[minmax(320px,380px)_1fr] lg:items-stretch xl:grid-cols-[minmax(360px,420px)_1fr]">
                    <section className="flex flex-1 flex-col overflow-hidden rounded-3xl bg-white/80 shadow-[0_45px_90px_-45px_rgba(15,23,42,0.6)] ring-1 ring-slate-200/60 backdrop-blur dark:bg-slate-900/70 dark:shadow-[0_45px_90px_-45px_rgba(15,23,42,0.85)] dark:ring-slate-800/60">
                        <div className="flex flex-1">
                            <ChatKitPanel
                                theme={scheme}
                                onThreadChange={handleThreadChange}
                                onResponseCompleted={handleResponseCompleted}
                            />
                        </div>
                    </section>

                    <div>
                        <h2 className="text-lg font-semibold text-slate-700 dark:text-slate-200">
                            Saved events/actions
                        </h2>
                        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                            Events and actions appear here after you share them in the conversation.
                        </p>
                        <div className="mt-6">
                            <div className="rounded-3xl border border-slate-200/60 bg-white/70 shadow-[0_35px_90px_-55px_rgba(15,23,42,0.45)] ring-1 ring-slate-200/50 backdrop-blur-sm dark:border-slate-800/70 dark:bg-slate-900/50 dark:shadow-[0_45px_95px_-60px_rgba(15,23,42,0.85)] dark:ring-slate-900/60">
                                <div className="max-h-[50vh] overflow-y-auto p-6 sm:max-h-[40vh]">

                                </div>
                            </div>
                        </div>
                    </div>
                </div>


            </div>
        </div>
    );
}
