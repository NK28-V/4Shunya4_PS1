import { NextResponse } from "next/server"
import type { ScanReport } from "@/lib/types" // Make sure this path is correct!

const mockScan: ScanReport = {
  id: "scan_001",
  projectName: "vibe-ai-repo",
  score: 80,
  codeCoverage: 72,
  criticalIssues: 3,
  alertingConfigured: false,
  availabilitySLO: 88,
  deploymentBlocked: true,
  createdAt: new Date().toISOString(),
  status: "COMPLETED",

  vulnerabilities: [
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
  ]
}

// This is what Next.js needs to handle the fetch() request
export async function GET() {
  return NextResponse.json(mockScan)
}