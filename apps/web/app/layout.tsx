import React from "react";
import "./globals.css";

export const metadata = {
  title: "KAIRO | Enterprise Work Continuity & Temporal Knowledge Engine",
  description: "Eliminate developer context loss during offboarding and transitions with verifiable proof and native desktop HUD.",
  icons: {
    icon: "/kairo.png",
    shortcut: "/kairo.png",
    apple: "/kairo.png",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="icon" href="/kairo.png" />
      </head>
      <body className="min-h-screen bg-slate-50 text-slate-900 antialiased">
        {children}
      </body>
    </html>
  );
}
