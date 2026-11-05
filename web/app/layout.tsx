import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FORM — Upper-body muscle identification",
  description: "Interactive front and back upper-body muscle identification and annotation.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}

