"use client";

import { useState, useRef, useEffect, FormEvent } from "react";
import { Send, ShieldAlert, Cpu } from "lucide-react";

interface Message {
    role: "user" | "assistant";
    content: string;
}

interface ChatWindowProps {
    apiUrl: string;
    userId: string;
    sessionId: string;
    messages: Message[];
    setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
}

export default function ChatWindow({ apiUrl, userId, sessionId, messages, setMessages }: ChatWindowProps) {
    const [input, setInput] = useState<string>("");
    const [loading, setLoading] = useState<boolean>(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, loading]);

    const handleSendMessage = async (e: FormEvent) => {
        e.preventDefault();
        if (!input.trim() || loading) return;

        const userQuery = input.trim();
        setInput("");

        // Stage the user's inquiry and provision a target workspace chunk for the streamed response
        setMessages((prev) => [
            ...prev,
            { role: "user", content: userQuery },
            { role: "assistant", content: "" }
        ]);
        setLoading(true);

        try {
            const response = await fetch(`${apiUrl}/chat`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    query: userQuery,
                    user_id: userId,
                    session_id: sessionId,
                }),
            });

            if (!response.ok) {
                throw new Error(`Inference Engine Exception: Status Code ${response.status}`);
            }

            if (!response.body) {
                throw new Error("ReadableStream interface unavailable on target response payload.");
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");
            let done = false;

            // Disable global spinner as token values begin streaming into the UI workspace
            setLoading(false);

            while (!done) {
                const { value, done: doneReading } = await reader.read();
                done = doneReading;

                const chunkValue = decoder.decode(value, { stream: !done });

                // Functional state mutation to attach text chunks directly to the current block frame
                setMessages((prev) => {
                    const updated = [...prev];
                    const lastIdx = updated.length - 1;
                    if (lastIdx >= 0 && updated[lastIdx].role === "assistant") {
                        updated[lastIdx].content += chunkValue;
                    }
                    return updated;
                });
            }
        } catch (error: any) {
            setLoading(false);
            setMessages((prev) => {
                const updated = [...prev];
                const lastIdx = updated.length - 1;
                if (lastIdx >= 0 && updated[lastIdx].role === "assistant") {
                    updated[lastIdx].content = `Network Communication Failure: Could not synchronize token blocks. ${error.message || ""}`;
                }
                return updated;
            });
        }
    };

    return (
        <div className="flex flex-1 flex-col overflow-hidden bg-slate-950">
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
                {messages.length === 0 && (
                    <div className="flex h-full flex-col items-center justify-center text-center max-w-md mx-auto space-y-3">
                        <div className="p-3 bg-slate-900 border border-slate-800 rounded-2xl text-emerald-400">
                            <Cpu className="h-6 w-6" />
                        </div>
                        <h3 className="text-sm font-medium text-white">Verified Legal Knowledge Namespace Connected</h3>
                        <p className="text-xs text-slate-400 leading-relaxed">
                            State your operational query or case incidents. System evaluation maps responses directly against structured Indian statutory references.
                        </p>
                    </div>
                )}

                {messages.map((msg, index) => {
                    // If the assistant message content is still empty and loading state is active, render nothing here
                    if (msg.role === "assistant" && !msg.content && loading) return null;

                    return (
                        <div
                            key={index}
                            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                        >
                            <div
                                className={`max-w-2xl rounded-xl px-4 py-2.5 text-sm shadow-md border ${msg.role === "user"
                                    ? "bg-emerald-600 border-emerald-500 text-white"
                                    : "bg-slate-900 border-slate-800 text-slate-200"
                                    }`}
                            >
                                <p className="whitespace-pre-line leading-relaxed">{msg.content}</p>
                            </div>
                        </div>
                    );
                })}

                {loading && (
                    <div className="flex justify-start">
                        <div className="bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-sm text-slate-400 shadow-md flex items-center space-x-2">
                            <div className="flex space-x-1">
                                <div className="h-1.5 w-1.5 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: "0ms" }}></div>
                                <div className="h-1.5 w-1.5 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: "150ms" }}></div>
                                <div className="h-1.5 w-1.5 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: "300ms" }}></div>
                            </div>
                            <span className="text-xs font-mono tracking-wide text-slate-500">Initializing streaming pipeline context channels...</span>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            <div className="p-4 border-t border-slate-800 bg-slate-900/60">
                <form onSubmit={handleSendMessage} className="flex items-center space-x-2 max-w-4xl mx-auto">
                    <input
                        type="text"
                        className="flex-1 bg-slate-950 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                        placeholder="Type your legal query here..."
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        disabled={loading}
                    />
                    <button
                        type="submit"
                        disabled={loading || !input.trim()}
                        className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white p-2.5 rounded-lg transition-colors focus:outline-none"
                    >
                        <Send className="h-4 w-4" />
                    </button>
                </form>
                <div className="flex items-center justify-center space-x-1.5 mt-2.5 text-[10px] text-slate-500">
                    <ShieldAlert className="h-3 w-3" />
                    <span>Context-grounded informational output. Verify independent legal findings before formal execution.</span>
                </div>
            </div>
        </div>
    );
}
