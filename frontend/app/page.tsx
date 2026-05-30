"use client";

import { useState, useEffect } from "react";
import AuthForm from "../components/AuthForm";
import Sidebar from "../components/Sidebar";
import ChatWindow from "../components/ChatWindow";

interface Message {
    role: "user" | "assistant";
    content: string;
}

interface ChatSession {
    id: string;
    title: string;
    messages: Message[];
}

export default function Home() {
    const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
    const [userId, setUserId] = useState<string>("");
    const [sessions, setSessions] = useState<ChatSession[]>([]);
    const [activeSessionId, setActiveSessionId] = useState<string>("");
    const [apiUrl, setApiUrl] = useState<string>("http://127.0.0.1:8000");

    useEffect(() => {
        if (process.env.NEXT_PUBLIC_API_URL) {
            setApiUrl(process.env.NEXT_PUBLIC_API_URL);
        }
    }, []);

    const handleLoginSuccess = (username: string) => {
        const primarySessionId = crypto.randomUUID();
        const initialSession: ChatSession = {
            id: primarySessionId,
            title: "New Legal Case",
            messages: []
        };
        setUserId(username);
        setSessions([initialSession]);
        setActiveSessionId(primarySessionId);
        setIsAuthenticated(true);
    };

    const handleSignOut = () => {
        setIsAuthenticated(false);
        setUserId("");
        setSessions([]);
        setActiveSessionId("");
    };

    const handleNewCase = () => {
        const nextSessionId = crypto.randomUUID();
        const nextSession: ChatSession = {
            id: nextSessionId,
            title: `Case File ${sessions.length + 1}`,
            messages: []
        };
        setSessions((prev) => [nextSession, ...prev]);
        setActiveSessionId(nextSessionId);
    };

    const handleSelectSession = (id: string) => {
        setActiveSessionId(id);
    };

    const handleUpdateMessages = (updatedMessages: Message[]) => {
        setSessions((prev) =>
            prev.map((session) =>
                session.id === activeSessionId
                    ? { ...session, messages: updatedMessages }
                    : session
            )
        );
    };

    const currentActiveSession = sessions.find((s) => s.id === activeSessionId);

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
                sessions={sessions}
                activeSessionId={activeSessionId}
                onNewCase={handleNewCase}
                onSelectSession={handleSelectSession}
                onSignOut={handleSignOut}
            />
            <main className="flex flex-1 flex-col overflow-hidden border-l border-slate-800">
                <header className="flex h-16 items-center justify-between border-b border-slate-800 bg-slate-900 px-6 shrink-0">
                    <h1 className="text-xl font-bold tracking-tight text-white">
                        AI-Powered Legal Assistant
                    </h1>
                    <div className="text-xs text-slate-400 bg-slate-800 px-3 py-1.5 rounded-md border border-slate-700">
                        Secure Thread: <span className="font-mono text-emerald-400">{activeSessionId.substring(0, 8)}...</span>
                    </div>
                </header>
                <ChatWindow
                    apiUrl={apiUrl}
                    userId={userId}
                    sessionId={activeSessionId}
                    messages={currentActiveSession ? currentActiveSession.messages : []}
                    setMessages={handleUpdateMessages}
                />
            </main>
        </div>
    );
}
