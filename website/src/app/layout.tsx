import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { AppSidebar } from "@/components/app-sidebar";
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { ThemeProvider } from "@/components/theme-provider";
import { ThemeToggle } from "@/components/theme-toggle";

const inter = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Congress Transparency | Surfacing Hidden Connections",
  description: "Surfacing the hidden connections between politics and markets. Track congressional trades, bill correlations, lobbying activity, and conflicts of interest.",
  keywords: ["congress", "stock trades", "financial disclosures", "lobbying", "transparency", "conflicts of interest", "political intelligence"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans antialiased`}>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <SidebarProvider>
            <AppSidebar />
            <SidebarInset>
              <header className="sticky top-0 z-10 flex h-16 items-center justify-between gap-4 border-b bg-background px-6">
                <div className="flex items-center gap-4">
                  <SidebarTrigger className="-ml-2" />
                  <div className="flex flex-col">
                    <span className="font-semibold text-foreground">Congress Transparency</span>
                    <span className="hidden text-xs text-muted-foreground md:inline">
                      Surfacing the Hidden Connections Between Politics and Markets
                    </span>
                  </div>
                </div>
                <ThemeToggle />
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
        </ThemeProvider>
      </body>
    </html>
  );
}
