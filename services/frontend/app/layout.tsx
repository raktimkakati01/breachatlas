import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { AtlasProvider } from "@/components/AtlasProvider";
import { UIProvider } from "@/components/UIProvider";
import Chrome from "@/components/Chrome";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono", display: "swap" });

export const metadata: Metadata = {
  title: "BreachAtlas — how breaches happened, and what would have stopped them",
  description:
    "A searchable, visual database of publicly reported data breaches, mapped to how they happened (MITRE ATT&CK) and which security controls would have prevented them (CIS Controls v8).",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${mono.variable}`}>
      <body className="min-h-screen antialiased">
        <AtlasProvider>
          <UIProvider>
            <div className="flex min-h-screen flex-col">
              <Chrome />
              <div className="flex-1">{children}</div>
            </div>
          </UIProvider>
        </AtlasProvider>
      </body>
    </html>
  );
}
