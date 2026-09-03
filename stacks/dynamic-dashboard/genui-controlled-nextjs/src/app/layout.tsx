import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "genui-controlled — dynamic dashboard PoC",
  description: "Controlled-tier generative UI: an LLM selects a prebuilt plot builder and fills its typed PlotSpec.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full">{children}</body>
    </html>
  );
}
