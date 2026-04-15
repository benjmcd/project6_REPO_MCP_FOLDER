import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NRC APS Review Sandbox",
  description:
    "Onlook sandbox for the NRC APS review surface, isolated from the live static UI.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
