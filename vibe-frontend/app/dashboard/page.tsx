"use client"

import { useQuery } from "@tanstack/react-query"
import { useState, useEffect, useMemo } from "react"
import VibeScorecard from "@/components/vibescorecard"
import type { ScanReport } from "@/lib/types"
import ErrorBoundary from "@/components/ErrorBoundary"
import ComplianceFlow from "@/components/ComplianceFlow"

const SCAN_ID = "scan_001"

function getScanApiBase(): string {
  const base = process.env.NEXT_PUBLIC_SCAN_API_BASE
  if (!base) return ""
  return base.replace(/\/$/, "")
}

async function fetchScan(scanId: string): Promise<ScanReport> {
  const base = getScanApiBase()
  if (!base) throw new Error("NEXT_PUBLIC_SCAN_API_BASE is not set")
  const url = `${base}/api/v1/scans/${scanId}`
  const res = await fetch(url)
  if (!res.ok) throw new Error("Failed to fetch scan")
  return res.json()
}

function ProcessingSkeleton() {
  return (
    <main className="min-h-screen bg-[#0B0B0C] text-white p-8 transition-all duration-700 ease-out">
      <div className="flex justify-between items-center border-b border-zinc-800 pb-4">
        <div className="h-6 w-48 bg-zinc-800 animate-pulse rounded" />
        <div className="h-6 w-20 bg-zinc-800 animate-pulse rounded" />
      </div>
      <section className="mt-10 flex justify-center">
        <div className="w-64 h-64 rounded-full border border-zinc-800 animate-pulse" />
      </section>
      <section className="mt-14 space-y-4">
        <div className="h-4 w-32 bg-zinc-800 animate-pulse rounded" />
        <div className="grid grid-cols-2 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-20 bg-zinc-800/60 animate-pulse rounded" />
          ))}
        </div>
      </section>
      <section className="mt-16">
        <div className="h-6 w-48 bg-zinc-800 animate-pulse rounded mb-6" />
        <div className="w-full h-[500px] bg-zinc-900/50 border border-zinc-800 rounded-md animate-pulse" />
      </section>
    </main>
  )
}

function SupplyChainAlertModal({
  onAcknowledge,
}: {
  onAcknowledge: () => void
}) {
  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/85 backdrop-blur-sm"
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="supply-chain-alert-title"
    >
      <div className="max-w-md mx-4 p-6 bg-[#1a1a1c] border-2 border-[#E10600] rounded-lg shadow-2xl">
        <h2
          id="supply-chain-alert-title"
          className="text-xl font-bold text-[#E10600] mb-2"
        >
          Supply Chain Alert
        </h2>
        <p className="text-zinc-300 text-sm mb-4">
          A CRITICAL vulnerability with AI-hallucinated dependency metadata was
          detected. Review and remediate before deployment.
        </p>
        <button
          onClick={onAcknowledge}
          className="w-full py-2 px-4 bg-[#E10600] hover:bg-[#c60500] text-white font-medium rounded transition-colors"
        >
          Acknowledge
        </button>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const [acknowledgedSupplyChainAlert, setAcknowledgedSupplyChainAlert] =
    useState(false)

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["scan", SCAN_ID],
    queryFn: () => fetchScan(SCAN_ID),
    refetchInterval: (query) =>
      query.state.data?.status === "PROCESSING" ? 5000 : false,
  })

  const isProcessing =
    isLoading || (!!data && data.status === "PROCESSING")

  const hasCriticalAiHallucinated = useMemo(() => {
    if (!data?.vulnerabilities) return false
    return data.vulnerabilities.some(
      (v) =>
        v.severity === "CRITICAL" &&
        Array.isArray(v.metadata) &&
        v.metadata.includes("AI_HALLUCINATED")
    )
  }, [data?.vulnerabilities])

  const showSupplyChainModal =
    hasCriticalAiHallucinated && !acknowledgedSupplyChainAlert

  if (error) {
    return (
      <div className="min-h-screen bg-[#0B0B0C] flex items-center justify-center">
        <div className="p-10 text-red-500 text-center">
          Scan failed to load.
        </div>
      </div>
    )
  }

  if (isProcessing) {
    return <ProcessingSkeleton />
  }

  if (!data) return null

  const effectiveData: ScanReport = data
  const isBlocked = effectiveData.score < 60

  return (
    <>
      {showSupplyChainModal && (
        <SupplyChainAlertModal
          onAcknowledge={() => setAcknowledgedSupplyChainAlert(true)}
        />
      )}
      <ErrorBoundary>
        <main className="min-h-screen bg-[#0B0B0C] text-white p-8">
          {/* HEADER */}
          <div className="flex justify-between items-center border-b border-zinc-800 pb-4">
            <div className="flex items-center gap-3">
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
            <ComplianceFlow dataFlow={effectiveData.dataFlow} />
          </section>
        </main>
      </ErrorBoundary>
    </>
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
