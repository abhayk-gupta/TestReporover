import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
    title: "LegalBuddy",
    description: "AI-Powered Legal Assistant",
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="en" className="h-full bg-slate-950">
            <body className="h-full antialiased font-sans text-slate-100">
                {children}
            </body>
        </html>
    );
}
