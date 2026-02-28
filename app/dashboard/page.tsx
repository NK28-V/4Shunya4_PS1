"use client"

import { useQuery } from "@tanstack/react-query"
import { useState, useEffect } from "react"
import VibeScorecard from "@/components/vibescorecard"
import type { ScanReport } from "@/lib/types"
import ErrorBoundary from "@/components/ErrorBoundary"
import ComplianceFlow from "@/components/ComplianceFlow"

async function fetchScan(): Promise<ScanReport> {
  const res = await fetch("/api/v1/scans/scan_001")
  if (!res.ok) throw new Error("Failed to fetch scan")
  return res.json()
}

export default function Dashboard() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["scan"],
    queryFn: fetchScan,
    refetchInterval: (query) =>
      query.state.data?.status === "PROCESSING" ? 5000 : false
  })

  const [demoState, setDemoState] = useState<"FAILED" | "FIXED">("FAILED")

  if (isLoading) {
    return (
        <main className="min-h-screen bg-[#0B0B0C] text-white p-8 transition-all duration-700 ease-in-out">
            <div
  key={demoState}
  className="transition-opacity duration-500">

        <div className="flex justify-between items-center border-b border-zinc-800 pb-4">
          <div className="h-6 w-48 bg-zinc-800 animate-pulse rounded" />
          <div className="h-6 w-20 bg-zinc-800 animate-pulse rounded" />
        </div>
        </div>
        <section className="mt-10 flex justify-center">
          <div className="w-64 h-64 rounded-full border border-zinc-800 animate-pulse" />
        </section>
      </main>
    )
  }

  if (error) {
    return <div className="p-10 text-red-500">Scan failed to load.</div>
  }

  if (!data) return null

  // ---------------- DEMO DATA ----------------

  const failedScan: ScanReport = {
    ...data,
    score: 45,
    deploymentBlocked: true,
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
      { from: "User Input", to: "API Endpoint", encrypted: true },
      { from: "API Endpoint", to: "Auth Middleware", encrypted: true },
      {
        from: "Auth Middleware",
        to: "Database",
        encrypted: false,
        containsPII: true
      }
    ]
  }

  const fixedScan: ScanReport = {
    ...data,
    score: 95,
    deploymentBlocked: false,
    status: "COMPLETED",
    vulnerabilities: [],
    dataFlow: [
      { from: "User Input", to: "API Endpoint", encrypted: true },
      { from: "API Endpoint", to: "Auth Middleware", encrypted: true },
      { from: "Auth Middleware", to: "Hashing Middleware", encrypted: true },
      {
        from: "Hashing Middleware",
        to: "Database",
        encrypted: true,
        containsPII: true
      }
    ]
  }

  const effectiveData =
    demoState === "FAILED" ? failedScan : fixedScan

  const isBlocked = effectiveData.score < 60

  return (
    <ErrorBoundary>
      <main className="min-h-screen bg-[#0B0B0C] text-white p-8">

        {/* HEADER */}
        <div className="flex justify-between items-center border-b border-zinc-800 pb-4">

          <div className="flex items-center gap-3">

            <button
              onClick={() =>
                setDemoState(prev =>
                  prev === "FAILED" ? "FIXED" : "FAILED"
                )
              }
              className="px-4 py-1 text-xs border border-zinc-700 hover:border-white transition-colors"
            >
              {demoState === "FAILED"
                ? "Simulate Remediation"
                : "Show Failure"}
            </button>

            <button
              onClick={() => refetch()}
              className="px-4 py-1 text-xs border border-zinc-700 hover:border-white transition-colors"
            >
              Re-run Scan
            </button>

            <div
  className={`px-4 py-1 text-sm font-semibold rounded-sm transition-all duration-500 ${
    isBlocked ? "bg-[#E10600] scale-100" : "bg-green-600 scale-105"
  }`}
>
              {isBlocked ? "NO-GO" : "GO"}
            </div>

          </div>
        </div>

        {/* SCORE */}
        <section className="mt-10 flex justify-center">
          <ScoreGauge score={effectiveData.score} />
        </section>

        {/* SCORECARD */}
        <section className="mt-14">
          <VibeScorecard data={effectiveData} />
        </section>

        {/* COMPLIANCE GRAPH */}
        <section className="mt-16">
          <h2 className="text-lg font-semibold mb-6">
            Compliance Data Flow
          </h2>

          <ComplianceFlow
            dataFlow={effectiveData.dataFlow}
          />
        </section>

      </main>
    </ErrorBoundary>
  )
}

// ---------------- SCORE GAUGE ----------------

function ScoreGauge({ score }: { score: number }) {
  const [displayScore, setDisplayScore] = useState(0)

  useEffect(() => {
    let start = 0
    const duration = 800
    const stepTime = 20
    const increment = score / (duration / stepTime)

    const interval = setInterval(() => {
      start += increment
      if (start >= score) {
        setDisplayScore(score)
        clearInterval(interval)
      } else {
        setDisplayScore(Math.floor(start))
      }
    }, stepTime)

    return () => clearInterval(interval)
  }, [score])

  const radius = 100
  const stroke = 14
  const normalizedRadius = radius - stroke * 0.5
  const circumference = normalizedRadius * 2 * Math.PI
  const strokeDashoffset =
    circumference - (displayScore / 100) * circumference

  const color =
    score >= 90
      ? "#16a34a"
      : score >= 70
      ? "#facc15"
      : "#E10600"

  return (
    <div className="relative w-64 h-64 flex items-center justify-center">
      <div
        className="absolute w-64 h-64 rounded-full blur-2xl opacity-20"
        style={{ backgroundColor: color }}
      />

      <svg
        height={radius * 2}
        width={radius * 2}
        className="transform -rotate-90"
      >
        <circle
          stroke="#1f1f1f"
          fill="transparent"
          strokeWidth={stroke}
          r={normalizedRadius}
          cx={radius}
          cy={radius}
        />

        <defs>
          <linearGradient id="gaugeGradient">
            <stop offset="0%" stopColor={color} />
            <stop offset="100%" stopColor="#ffffff" stopOpacity="0.2" />
          </linearGradient>
        </defs>

        <circle
          stroke="url(#gaugeGradient)"
          fill="transparent"
          strokeWidth={stroke}
          strokeDasharray={`${circumference} ${circumference}`}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          r={normalizedRadius}
          cx={radius}
          cy={radius}
          className="transition-all duration-1000 ease-out"
        />
      </svg>

      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
        <span
          className="text-5xl font-bold tracking-wide"
          style={{ color }}
        >
          {displayScore}
        </span>

        <span className="text-xs tracking-[0.3em] text-zinc-500 mt-2">
          VIBE SCORE
        </span>
      </div>
    </div>
  )
}