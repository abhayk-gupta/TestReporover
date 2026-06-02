"use client";

import { useState, useRef, useEffect, FormEvent } from "react";
import { Send, ShieldAlert, Cpu, Loader2, Copy, Check } from "lucide-react";
import ReactMarkdown from 'react-markdown';
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";

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
    const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

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

            if (!response.ok) throw new Error(`Status: ${response.status}`);
            if (!response.body) throw new Error("No response stream");

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
                    if (isFirstChunk) { setIsProcessing(false); isFirstChunk = false; }
                    setMessages([...stagedMessages, { role: "assistant", content: combinedStreamText }]);
                }
            }
        } catch (error: any) {
            setIsProcessing(false);
            toast.error("Failed to connect to the legal assistant.");
        }
    };

    const copyToClipboard = (text: string, index: number) => {
        navigator.clipboard.writeText(text);
        setCopiedIndex(index);
        setTimeout(() => setCopiedIndex(null), 2000);
    };

    return (
        <div className="flex flex-1 flex-col overflow-hidden bg-slate-950">
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
                {messages.length === 0 && !isProcessing && (
                    <div className="flex h-full flex-col items-center justify-center text-center max-w-lg mx-auto space-y-4">
                        <div className="p-4 bg-slate-900 border border-slate-800 rounded-2xl text-emerald-400">
                            <Cpu className="h-8 w-8" />
                        </div>
                        <h3 className="text-lg font-bold text-white">LegalBuddy AI</h3>
                        <p className="text-sm text-slate-400">State your query to begin context-grounded legal analysis.</p>
                    </div>
                )}

                <AnimatePresence>
                    {messages.map((msg, index) => (
                        <motion.div
                            key={index}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                        >
                            <div className={`max-w-3xl rounded-2xl px-5 py-3.5 border ${msg.role === "user" ? "bg-emerald-600 border-emerald-500 text-white" : "bg-slate-900 border-slate-800 text-slate-100"}`}>
                                <div className="prose prose-invert prose-emerald prose-sm max-w-none">
                                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                                </div>
                                {msg.role === "assistant" && (
                                    <button 
                                        onClick={() => copyToClipboard(msg.content, index)}
                                        className="mt-3 text-slate-500 hover:text-white transition-colors"
                                    >
                                        {copiedIndex === index ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                                    </button>
                                )}
                            </div>
                        </motion.div>
                    ))}
                </AnimatePresence>

                {isProcessing && (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex justify-start">
                        <div className="bg-slate-900 border border-slate-800 rounded-2xl px-5 py-4 flex items-center space-x-3">
                            <Loader2 className="h-5 w-5 text-emerald-500 animate-spin" />
                            <span className="text-sm text-slate-400">Processing context...</span>
                        </div>
                    </motion.div>
                )}
                <div ref={messagesEndRef} />
            </div>

            <div className="p-4 border-t border-slate-800 bg-slate-900/60">
                <form onSubmit={handleSendMessage} className="flex items-center space-x-3 max-w-5xl mx-auto">
                    <input
                        type="text"
                        className="flex-1 bg-slate-950 border border-slate-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                        placeholder="State your legal question..."
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        disabled={isProcessing}
                    />
                    <button
                        type="submit"
                        disabled={isProcessing || !input.trim()}
                        className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white p-3 rounded-xl transition-all"
                    >
                        <Send className="h-5 w-5" />
                    </button>
                </form>
            </div>
        </div>
    );
}

