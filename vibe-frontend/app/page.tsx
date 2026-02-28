"use client"

import { useRouter } from "next/navigation"
import { useState } from "react"

function getScanApiBase(): string {
  const base = process.env.NEXT_PUBLIC_SCAN_API_BASE
  if (!base) return ""
  return base.replace(/\/$/, "")
}

export default function Landing() {
  const router = useRouter()
  const [repoUrl, setRepoUrl] = useState("")
  const [isTransitioning, setIsTransitioning] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleRunScan = async () => {
    const trimmed = repoUrl.trim()
    if (!trimmed) {
      setError("Please enter a GitHub repository URL.")
      return
    }

    const base = getScanApiBase()
    if (!base) {
      setError("Scan API is not configured (NEXT_PUBLIC_SCAN_API_BASE).")
      return
    }

    setError(null)
    setIsLoading(true)

    try {
      // a) POST /api/v1/projects/
      const projectRes = await fetch(`${base}/api/v1/projects/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: "Dynamic Project",
          repository_url: trimmed,
        }),
      })
      if (!projectRes.ok) {
        const errBody = await projectRes.text()
        throw new Error(errBody || `Project creation failed: ${projectRes.status}`)
      }
      const projectData = await projectRes.json()
      const projectId = projectData.id
      if (projectId == null) {
        throw new Error("Project response missing id")
      }

      // b) POST /api/v1/scans/{project_id}/trigger
      const triggerRes = await fetch(
        `${base}/api/v1/scans/${projectId}/trigger`,
        { method: "POST" }
      )
      if (!triggerRes.ok) {
        const errBody = await triggerRes.text()
        throw new Error(errBody || `Trigger scan failed: ${triggerRes.status}`)
      }
      const triggerData = await triggerRes.json()
      const scanId = triggerData.scan_id ?? triggerData.id ?? triggerData.scanId
      if (scanId == null) {
        throw new Error("Trigger response missing scan_id")
      }

      setIsTransitioning(true)
      setTimeout(() => {
        router.push(`/dashboard?scanId=${encodeURIComponent(String(scanId))}`)
      }, 600)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start scan.")
      setIsLoading(false)
    }
  }

  return (
    <main
      className={`relative min-h-screen bg-[#0B0B0C] text-white overflow-hidden transition-opacity duration-700 ${
        isTransitioning ? "opacity-0" : "opacity-100"
      }`}
    >
      {/* Grid */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#1a1a1a_1px,transparent_1px),linear-gradient(to_bottom,#1a1a1a_1px,transparent_1px)] bg-[size:40px_40px] opacity-20 pointer-events-none" />

      {/* Content */}
      <div className="relative z-10 flex flex-col items-center justify-center min-h-screen text-center px-6">
        <h1 className="text-5xl md:text-6xl font-bold tracking-wide">
          VIBE-AUDIT
        </h1>

        <p className="mt-6 text-zinc-400 max-w-xl text-lg">
          From Vibe to Value. Production-grade security for AI-generated
          applications.
        </p>

        <div className="mt-10 w-full max-w-md">
          <label htmlFor="repo-url" className="sr-only">
            GitHub Repository URL
          </label>
          <input
            id="repo-url"
            type="url"
            placeholder="https://github.com/owner/repo"
            value={repoUrl}
            onChange={(e) => setRepoUrl(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleRunScan()}
            disabled={isLoading}
            className="w-full px-4 py-3 bg-zinc-900 border border-zinc-700 rounded text-white placeholder-zinc-500 focus:outline-none focus:border-[#E10600] focus:ring-1 focus:ring-[#E10600] transition-colors disabled:opacity-60"
            aria-invalid={!!error}
            aria-describedby={error ? "repo-error" : undefined}
          />
          {error && (
            <p
              id="repo-error"
              role="alert"
              className="mt-2 text-sm text-[#E10600]"
            >
              {error}
            </p>
          )}
        </div>

        <button
          onClick={handleRunScan}
          disabled={isLoading}
          className="mt-6 px-8 py-3 border border-[#E10600] text-[#E10600] hover:bg-[#E10600] hover:text-black transition-all duration-300 disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {isLoading ? "Starting scan…" : "Run Production Scan →"}
        </button>
      </div>
    </main>
  )
}
