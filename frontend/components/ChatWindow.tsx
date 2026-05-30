"use client";

import { useState, useRef, useEffect, FormEvent } from "react";
import { Send, ShieldAlert, Cpu, Loader2 } from "lucide-react";

interface Message {
    role: "user" | "assistant";
    content: string;
}

interface ChatWindowProps {
    apiUrl: string;
    userId: string;
    sessionId: string;
    messages: Message[];
    setMessages: (messages: Message[]) => void;
}

export default function ChatWindow({ apiUrl, userId, sessionId, messages, setMessages }: ChatWindowProps) {
    const [input, setInput] = useState<string>("");
    const [isProcessing, setIsProcessing] = useState<boolean>(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isProcessing]);

    const handleSendMessage = async (e: FormEvent) => {
        e.preventDefault();
        if (!input.trim() || isProcessing) return;

        const userQuery = input.trim();
        setInput("");

        // Build history array with safety checks to prevent text duplication
        const stagedMessages: Message[] = [
            ...messages,
            { role: "user", content: userQuery }
        ];

        setMessages(stagedMessages);
        setIsProcessing(true);

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
            let combinedStreamText = "";
            let isFirstChunk = true;

            while (!done) {
                const { value, done: doneReading } = await reader.read();
                done = doneReading;

                const chunkValue = decoder.decode(value || new Uint8Array(), { stream: !done });
                if (chunkValue) {
                    combinedStreamText += chunkValue;

                    if (isFirstChunk) {
                        // Deactivate loading animation as the first block of text arrives
                        setIsProcessing(false);
                        isFirstChunk = false;
                    }

                    // Append the streaming content safely onto the current assistant index
                    setMessages([...stagedMessages, { role: "assistant", content: combinedStreamText }]);
                }
            }
        } catch (error: any) {
            setIsProcessing(false);
            setMessages([
                ...stagedMessages,
                {
                    role: "assistant",
                    content: `Network Communication Failure: Could not synchronize token blocks. ${error.message || ""}`
                }
            ]);
        }
    };

    return (
        <div className="flex flex-1 flex-col overflow-hidden bg-slate-950">
            {/* SCROLLABLE CONVERSATION LOGS PANEL */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
                {messages.length === 0 && !isProcessing && (
                    <div className="flex h-full flex-col items-center justify-center text-center max-w-lg mx-auto space-y-4">
                        <div className="p-4 bg-slate-900 border border-slate-800 rounded-2xl text-emerald-400 shadow-xl">
                            <Cpu className="h-8 w-8" />
                        </div>
                        <h3 className="text-lg font-bold text-white">Verified Legal Knowledge Namespace Connected</h3>
                        <p className="text-sm text-slate-400 leading-relaxed">
                            State your operational query or case incidents. System evaluation maps responses directly against structured Indian statutory references.
                        </p>
                    </div>
                )}

                {messages.map((msg, index) => (
                    <div
                        key={index}
                        className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                    >
                        <div
                            className={`max-w-3xl rounded-xl px-5 py-3.5 shadow-lg border text-base leading-relaxed ${msg.role === "user"
                                ? "bg-emerald-600 border-emerald-500 text-white font-medium"
                                : "bg-slate-900 border-slate-800 text-slate-100"
                                }`}
                        >
                            <p className="whitespace-pre-line">{msg.content}</p>
                        </div>
                    </div>
                ))}

                {/* PERSISTENT PROCESSING VISUAL STATE */}
                {isProcessing && (
                    <div className="flex justify-start animate-fade-in">
                        <div className="bg-slate-900 border border-slate-800 rounded-xl px-5 py-4 shadow-lg flex items-center space-x-3">
                            <Loader2 className="h-5 w-5 text-emerald-500 animate-spin" />
                            <span className="text-sm font-mono tracking-wide text-slate-400">
                                LegalBuddy is running context grading nodes...
                            </span>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* LOWER CONTROL INPUT FOOTER CHANNELS */}
            <div className="p-4 border-t border-slate-800 bg-slate-900/60 shrink-0">
                <form onSubmit={handleSendMessage} className="flex items-center space-x-3 max-w-5xl mx-auto">
                    <input
                        type="text"
                        className="flex-1 bg-slate-950 border border-slate-700 rounded-lg px-4 py-3 text-base text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                        placeholder="Type your legal query here..."
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        disabled={isProcessing}
                    />
                    <button
                        type="submit"
                        disabled={isProcessing || !input.trim()}
                        className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 disabled:hover:bg-emerald-600 text-white p-3 rounded-lg transition-colors focus:outline-none shrink-0"
                    >
                        <Send className="h-5 w-5" />
                    </button>
                </form>
                <div className="flex items-center justify-center space-x-1.5 mt-3 text-xs text-slate-500">
                    <ShieldAlert className="h-3.5 w-3.5 text-slate-500" />
                    <span>Context-grounded informational output. Verify independent legal findings before formal execution.</span>
                </div>
            </div>
        </div>
    );
}
