import "./globals.css";

import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Park English",
  description: "A 3D multiplayer island for adults to practise English by talking.",
};

export const viewport: Viewport = { width: "device-width", initialScale: 1 };

const RootLayout = ({ children }: { children: ReactNode }) => (
  <html lang="en">
    <body>{children}</body>
  </html>
);

export default RootLayout;
