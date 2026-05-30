"use client";

import { useState, useEffect } from "react";
import AuthForm from "../components/AuthForm";
import Sidebar from "../components/Sidebar";
import ChatWindow from "../components/ChatWindow";

interface Message {
    role: "user" | "assistant";
    content: string;
}

export default function Home() {
    const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
    const [userId, setUserId] = useState<string>("");
    const [sessionId, setSessionId] = useState<string>("");
    const [messages, setMessages] = useState<Message[]>([]);
    const [apiUrl, setApiUrl] = useState<string>("http://127.0.0.1:8000");

    useEffect(() => {
        if (process.env.NEXT_PUBLIC_API_URL) {
            setApiUrl(process.env.NEXT_PUBLIC_API_URL);
        }
    }, []);

    const handleLoginSuccess = (username: string) => {
        const generatedSessionId = crypto.randomUUID();
        setUserId(username);
        setSessionId(generatedSessionId);
        setIsAuthenticated(true);
        setMessages([]);
    };

    const handleSignOut = () => {
        setIsAuthenticated(false);
        setUserId("");
        setSessionId("");
        setMessages([]);
    };

    const handleNewCase = () => {
        setSessionId(crypto.randomUUID());
        setMessages([]);
    };

    if (!isAuthenticated) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-slate-900 px-4 py-12 sm:px-6 lg:px-8">
                <div className="w-full max-w-md space-y-8 bg-slate-800 p-8 rounded-xl shadow-2xl border border-slate-700">
                    <div className="text-center">
                        <h2 className="mt-2 text-3xl font-bold tracking-tight text-white">
                            LegalBuddy
                        </h2>
                        <p className="mt-2 text-sm text-slate-400">
                            Identity Access Verification
                        </p>
                    </div>
                    <AuthForm apiUrl={apiUrl} onAuthSuccess={handleLoginSuccess} />
                </div>
            </div>
        );
    }

    return (
        <div className="flex h-screen bg-slate-950 text-slate-100 overflow-hidden">
            <Sidebar
                userId={userId}
                sessionId={sessionId}
                onNewCase={handleNewCase}
                onSignOut={handleSignOut}
            />
            <main className="flex flex-1 flex-col overflow-hidden border-l border-slate-800">
                <header className="flex h-16 items-center justify-between border-b border-slate-800 bg-slate-900 px-6">
                    <h1 className="text-lg font-semibold text-white">
                        AI-Powered Legal Assistant
                    </h1>
                    <div className="text-xs text-slate-400 bg-slate-800 px-3 py-1.5 rounded-md border border-slate-700">
                        Secure Thread: <span className="font-mono text-emerald-400">{sessionId.substring(0, 8)}...</span>
                    </div>
                </header>
                <ChatWindow
                    apiUrl={apiUrl}
                    userId={userId}
                    sessionId={sessionId}
                    messages={messages}
                    setMessages={setMessages}
                />
            </main>
        </div>
    );
}
