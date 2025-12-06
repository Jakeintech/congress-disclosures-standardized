import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { MainNav } from "@/components/nav/main-nav";

const inter = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Congress Financial Disclosures | Transparency Platform",
  description: "Track congressional stock trades, bill correlations, and lobbying activity. A transparency platform for monitoring potential conflicts of interest.",
  keywords: ["congress", "stock trades", "financial disclosures", "lobbying", "transparency"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.variable} font-sans antialiased min-h-screen bg-background`}>
        <MainNav />
        <main className="container mx-auto px-4 py-8 md:px-8 md:py-12">
          {children}
        </main>
        <footer className="border-t py-6 md:py-8">
          <div className="container mx-auto px-4 flex flex-col items-center justify-between gap-4 md:flex-row md:px-8">
            <p className="text-center text-sm text-muted-foreground">
              Built for transparency. Data sourced from public congressional records.
            </p>
            <p className="text-sm text-muted-foreground">
              <a href="https://github.com/Jakeintech/congress-disclosures-standardized"
                target="_blank"
                rel="noopener noreferrer"
                className="hover:underline">
                Open Source
              </a>
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
