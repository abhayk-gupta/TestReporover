"use client";

import { useState, FormEvent } from "react";
import { Eye, EyeOff, Shield, Loader2 } from "lucide-react";
import { toast } from "sonner";

interface AuthFormProps {
    apiUrl: string;
    onAuthSuccess: (username: string) => void;
}

export default function AuthForm({ apiUrl, onAuthSuccess }: AuthFormProps) {
    const [isLogin, setIsLogin] = useState<boolean>(true);
    const [username, setUsername] = useState<string>("");
    const [password, setPassword] = useState<string>("");
    const [showPassword, setShowPassword] = useState<boolean>(false);
    const [loading, setLoading] = useState<boolean>(false);

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        setLoading(true);

        if (!username || !password) {
            toast.error("Missing username or password.");
            setLoading(false);
            return;
        }

        const endpoint = isLogin ? `${apiUrl}/login` : `${apiUrl}/register`;

        try {
            const response = await fetch(endpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, password }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || "Authentication failed.");
            }

            if (isLogin) {
                toast.success("Successfully signed in.");
                onAuthSuccess(username);
            } else {
                toast.success("Account created successfully. Please sign in.");
                setIsLogin(true);
                setPassword("");
            }
        } catch (err: any) {
            toast.error(err.message || "Connection error.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="w-full max-w-sm mx-auto space-y-6 p-6 bg-slate-900 rounded-2xl border border-slate-800 shadow-2xl">
            <div className="flex border-b border-slate-700">
                <button
                    type="button"
                    className={`flex-1 pb-3 text-sm font-semibold text-center border-b-2 transition-all ${isLogin ? "border-emerald-500 text-white" : "border-transparent text-slate-500 hover:text-slate-300"
                        }`}
                    onClick={() => setIsLogin(true)}
                >
                    Sign In
                </button>
                <button
                    type="button"
                    className={`flex-1 pb-3 text-sm font-semibold text-center border-b-2 transition-all ${!isLogin ? "border-emerald-500 text-white" : "border-transparent text-slate-500 hover:text-slate-300"
                        }`}
                    onClick={() => setIsLogin(false)}
                >
                    Register
                </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                    <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">
                        Username
                    </label>
                    <input
                        type="text"
                        required
                        className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all"
                        placeholder="Enter username"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                    />
                </div>

                <div>
                    <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">
                        Password
                    </label>
                    <div className="relative">
                        <input
                            type={showPassword ? "text" : "password"}
                            required
                            className="w-full bg-slate-950 border border-slate-700 rounded-lg pl-3 pr-9 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all"
                            placeholder="Enter password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                        />
                        <button
                            type="button"
                            onClick={() => setShowPassword(!showPassword)}
                            className="absolute inset-y-0 right-0 px-2.5 flex items-center text-slate-500 hover:text-slate-300"
                        >
                            {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                        </button>
                    </div>
                </div>

                <button
                    type="submit"
                    disabled={loading}
                    className="w-full mt-4 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-sm py-2.5 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
                >
                    {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Shield className="h-4 w-4" />}
                    <span>{loading ? "Processing..." : isLogin ? "Sign In" : "Register"}</span>
                </button>
            </form>
        </div>
    );
}
