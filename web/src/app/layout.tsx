import type { Metadata } from "next";
import { IBM_Plex_Sans, IBM_Plex_Mono, Noto_Sans_Sinhala } from "next/font/google";

import { Providers, themeBootstrapScript } from "@/components/providers";
import "./globals.css";

const ui = IBM_Plex_Sans({
  variable: "--font-ui",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

const numeric = IBM_Plex_Mono({
  variable: "--font-num",
  subsets: ["latin"],
  weight: ["400", "500"],
});

// Sinhala previously fell back to whatever the OS had; names and risk narratives
// render in Sinhala throughout, so the face ships with the app.
const sinhala = Noto_Sans_Sinhala({
  variable: "--font-sinhala",
  subsets: ["sinhala"],
  weight: ["400", "500", "600"],
});

export const metadata: Metadata = {
  title: "Student Wellbeing Monitoring",
  description:
    "Early-support screening and learning intelligence for Sri Lankan schools. Decision support for teachers and counsellors; not a diagnostic system.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        {/* Applies the stored theme before first paint, so surfaces never flash. */}
        <script dangerouslySetInnerHTML={{ __html: themeBootstrapScript }} />
      </head>
      <body className={`${ui.variable} ${numeric.variable} ${sinhala.variable}`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
