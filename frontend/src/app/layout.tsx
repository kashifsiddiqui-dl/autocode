import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Auto Code - Medical Coding Assistant",
  description:
    "AI-powered medical coding assistant for ICD-10-CM code suggestions, validation, and export.",
  keywords: ["medical coding", "ICD-10-CM", "AI", "healthcare"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="font-sans antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
