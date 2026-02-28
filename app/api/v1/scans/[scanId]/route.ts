import { NextResponse } from "next/server"
import type { ScanReport } from "@/lib/types"

let progress = 0

export async function GET() {
  // Simulate backend processing
  if (progress < 100) {
    progress += 20
  }

  const isProcessing = progress < 100

const response: ScanReport = {
  id: "scan_001",
  projectName: "vibe-ai-repo",
  score: 45,
  codeCoverage: 72,
  criticalIssues: 3,
  alertingConfigured: false,
  availabilitySLO: 88,
  deploymentBlocked: true,
  createdAt: new Date().toISOString(),
  status: isProcessing ? "PROCESSING" : "COMPLETED",

  vulnerabilities: isProcessing
    ? []
    : [
        {
          id: "vuln_001",
          file: "package.json",
          severity: "CRITICAL",
          title: "Hallucinated npm package",
          metadata: ["AI_HALLUCINATED"]
        }
      ],

  dataFlow: [
    {
      from: "User Input",
      to: "API Endpoint",
      encrypted: true,
    },
    {
      from: "API Endpoint",
      to: "Auth Middleware",
      encrypted: true,
    },
    {
      from: "Auth Middleware",
      to: "Database",
      encrypted: false,
      containsPII: true,
    },
  ],
}

return NextResponse.json(response)
}