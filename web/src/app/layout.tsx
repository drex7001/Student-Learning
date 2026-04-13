import type { Metadata } from "next";
import { IBM_Plex_Mono, Space_Grotesk } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
});

const plexMono = IBM_Plex_Mono({
  variable: "--font-plex-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "KG Learning Intelligence System",
  description: "Grade 8 algebra diagnosis workspace backed by graph traversal and synthetic mastery data.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${spaceGrotesk.variable} ${plexMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <header className="sticky top-0 z-40 border-b border-white/8 bg-[rgba(250,247,241,0.78)] backdrop-blur-xl">
          <div className="flex w-full items-center justify-between gap-4 px-4 py-3 md:px-6 xl:px-8">
            <Link href="/" className="flex items-center gap-3 text-foreground">
              <span className="rounded-full bg-foreground px-3 py-2 font-mono text-[11px] uppercase tracking-[0.26em] text-white">
                KG
              </span>
              <div>
                <strong className="block text-sm uppercase tracking-[0.2em]">Learning Intelligence</strong>
                <span className="block text-xs text-muted">Teacher workflow MVP</span>
              </div>
            </Link>

            <nav className="flex flex-wrap items-center gap-2">
              <Link
                href="/"
                className="rounded-full px-4 py-2 text-sm text-muted transition-colors hover:bg-white/70 hover:text-foreground"
              >
                Home
              </Link>
              <Link
                href="/students"
                className="rounded-full px-4 py-2 text-sm text-muted transition-colors hover:bg-white/70 hover:text-foreground"
              >
                Support Queue
              </Link>
              <Link
                href="/diagnosis"
                className="rounded-full px-4 py-2 text-sm text-muted transition-colors hover:bg-white/70 hover:text-foreground"
              >
                Student Diagnosis
              </Link>
              <Link
                href="/concepts"
                className="rounded-full px-4 py-2 text-sm text-muted transition-colors hover:bg-white/70 hover:text-foreground"
              >
                Concept Explorer
              </Link>
            </nav>
          </div>
        </header>

        {children}
      </body>
    </html>
  );
}
