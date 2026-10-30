import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Form — Upper-body vision",
  description: "Pose-guided visual muscle annotations for a single back photo.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}

