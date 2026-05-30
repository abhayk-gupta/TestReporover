"use client";

import { Briefcase, LogOut, User, Scale } from "lucide-react";

interface SidebarProps {
    userId: string;
    sessionId: string;
    onNewCase: () => void;
    onSignOut: () => void;
}

export default function Sidebar({ userId, sessionId, onNewCase, onSignOut }: SidebarProps) {
    return (
        <aside className="w-64 bg-slate-900 flex flex-col justify-between border-r border-slate-800">
            <div className="p-6 space-y-6">
                <div className="flex items-center space-x-3">
                    <Scale className="h-6 w-6 text-emerald-500" />
                    <span className="text-xl font-bold text-white tracking-tight">LegalBuddy</span>
                </div>

                <button
                    onClick={onNewCase}
                    className="w-full flex items-center justify-center space-x-2 bg-slate-800 hover:bg-slate-700 text-emerald-400 hover:text-emerald-300 font-medium text-sm py-2 px-4 rounded-lg border border-slate-700 transition-colors"
                >
                    <Briefcase className="h-4 w-4" />
                    <span>New Case File</span>
                </button>
            </div>

            <div className="p-4 border-t border-slate-800 bg-slate-950/40 space-y-3">
                <div className="flex items-center space-x-3 px-2 py-1.5">
                    <div className="bg-slate-800 p-2 rounded-full border border-slate-700">
                        <User className="h-4 w-4 text-slate-300" />
                    </div>
                    <div className="overflow-hidden">
                        <p className="text-xs text-slate-400 font-medium">Active Security Profile</p>
                        <p className="text-sm font-semibold text-white truncate">{userId}</p>
                    </div>
                </div>

                <button
                    onClick={onSignOut}
                    className="w-full flex items-center space-x-2 text-slate-400 hover:text-red-400 hover:bg-red-950/20 px-3 py-2 rounded-lg text-xs font-medium transition-colors"
                >
                    <LogOut className="h-4 w-4" />
                    <span>Sign Out Session</span>
                </button>
            </div>
        </aside>
    );
}
