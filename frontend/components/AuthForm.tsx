"use client";

import { useState, FormEvent } from "react";
import { Eye, EyeOff, Shield } from "lucide-react";

interface AuthFormProps {
    apiUrl: string;
    onAuthSuccess: (username: string) => void;
}

export default function AuthForm({ apiUrl, onAuthSuccess }: AuthFormProps) {
    const [isLogin, setIsLogin] = useState<boolean>(true);
    const [username, setUsername] = useState<string>("");
    const [password, setPassword] = useState<string>("");
    const [showPassword, setShowPassword] = useState<boolean>(false);
    const [error, setError] = useState<string>("");
    const [successMessage, setSuccessMessage] = useState<string>("");
    const [loading, setLoading] = useState<boolean>(false);

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        setError("");
        setSuccessMessage("");
        setLoading(true);

        if (!username || !password) {
            setError("Missing username or password specifications.");
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
                throw new Error(data.detail || "Authentication processing anomaly experienced.");
            }

            if (isLogin) {
                onAuthSuccess(username);
            } else {
                setSuccessMessage("Account securely provisioned. Proceed to the sign in interface.");
                setIsLogin(true);
                setPassword("");
                setShowPassword(false);
            }
        } catch (err: any) {
            setError(err.message || "Target core service authentication node unreachable.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-6">
            <div className="flex border-b border-slate-700">
                <button
                    type="button"
                    className={`flex-1 pb-3 text-sm font-medium text-center border-b-2 transition-colors ${isLogin ? "border-emerald-500 text-white" : "border-transparent text-slate-400 hover:text-slate-200"
                        }`}
                    onClick={() => { setIsLogin(true); setError(""); setShowPassword(false); }}
                >
                    Sign In
                </button>
                <button
                    type="button"
                    className={`flex-1 pb-3 text-sm font-medium text-center border-b-2 transition-colors ${!isLogin ? "border-emerald-500 text-white" : "border-transparent text-slate-400 hover:text-slate-200"
                        }`}
                    onClick={() => { setIsLogin(false); setError(""); setShowPassword(false); }}
                >
                    Register Account
                </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
                {error && (
                    <div className="p-3 text-xs bg-red-950/50 border border-red-800 text-red-400 rounded-lg">
                        {error}
                    </div>
                )}
                {successMessage && (
                    <div className="p-3 text-xs bg-emerald-950/50 border border-emerald-800 text-emerald-400 rounded-lg">
                        {successMessage}
                    </div>
                )}

                <div>
                    <label className="block text-xs font-medium text-slate-400 uppercase tracking-wider mb-1.5">
                        Username
                    </label>
                    <input
                        type="text"
                        required
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 text-base"
                        placeholder="Case sensitive text sequence"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                    />
                </div>

                <div>
                    <label className="block text-xs font-medium text-slate-400 uppercase tracking-wider mb-1.5">
                        Password
                    </label>
                    <div className="relative">
                        <input
                            type={showPassword ? "text" : "password"}
                            required
                            className="w-full bg-slate-900 border border-slate-700 rounded-lg pl-3 pr-10 py-2 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 text-base"
                            placeholder="Secure cryptographic sequence"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                        />
                        <button
                            type="button"
                            onClick={() => setShowPassword(!showPassword)}
                            className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-200 transition-colors"
                        >
                            {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                        </button>
                    </div>
                </div>

                <button
                    type="submit"
                    disabled={loading}
                    className="w-full mt-2 bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-base py-2.5 px-4 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2 focus:ring-offset-slate-800 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
                >
                    <Shield className="h-4 w-4" />
                    <span>{loading ? "Verifying Credentials..." : isLogin ? "Sign In" : "Create Account"}</span>
                </button>
            </form>
        </div>
    );
}
