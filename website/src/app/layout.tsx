import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { AppSidebar } from "@/components/app-sidebar";
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";

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
      <body className={`${inter.variable} font-sans antialiased`}>
        <SidebarProvider>
          <AppSidebar />
          <SidebarInset>
            <header className="sticky top-0 z-10 flex h-16 items-center gap-4 border-b bg-background px-6">
              <SidebarTrigger className="-ml-2" />
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <span className="font-semibold">Congress Transparency</span>
                <span className="hidden md:inline">• Real-time tracking of congressional activity</span>
              </div>
            </header>
            <main className="flex-1 p-6 md:p-8">
              {children}
            </main>
            <footer className="border-t py-6 px-6">
              <div className="flex flex-col items-center justify-between gap-4 md:flex-row">
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
          </SidebarInset>
        </SidebarProvider>
      </body>
    </html>
  );
}
