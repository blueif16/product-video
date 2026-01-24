import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { CopilotKit } from "@copilotkit/react-core";
import "@copilotkit/react-ui/styles.css";
import { ErrorBoundary } from "@/components/ErrorBoundary";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "StreamLine - AI Video Production",
  description: "Create Product Hunt quality videos with AI",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <ErrorBoundary>
          <CopilotKit runtimeUrl="/api/copilotkit" agent="pipelineAgent">
            {children}
          </CopilotKit>
        </ErrorBoundary>
      </body>
    </html>
  );
}
