"use client"

import dynamic from "next/dynamic"
import { useRouter } from "next/navigation"
import { useState } from "react"

export default function Landing() {
  const router = useRouter()
  const [isTransitioning, setIsTransitioning] = useState(false)

  const handleStart = () => {
    setIsTransitioning(true)

    setTimeout(() => {
      router.push("/dashboard")
    }, 800) // delay before navigation
  }

  return (
    <main className={`relative min-h-screen bg-[#0B0B0C] text-white overflow-hidden transition-opacity duration-700 ${isTransitioning ? "opacity-0" : "opacity-100"}`}>

      {/* Grid */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#1a1a1a_1px,transparent_1px),linear-gradient(to_bottom,#1a1a1a_1px,transparent_1px)] bg-[size:40px_40px] opacity-20 pointer-events-none" />

      {/* Content */}
      <div className="relative z-10 flex flex-col items-center justify-center min-h-screen text-center px-6">
        
        <h1 className="text-5xl md:text-6xl font-bold tracking-wide">
          VIBE-AUDIT
        </h1>

        <p className="mt-6 text-zinc-400 max-w-xl text-lg">
          From Vibe to Value.
          Production-grade security for AI-generated applications.
        </p>

        <button
          onClick={handleStart}
          className="mt-10 px-8 py-3 border border-[#E10600] text-[#E10600] hover:bg-[#E10600] hover:text-black transition-all duration-300"
        >
          Run Production Scan →
        </button>

      </div>
    </main>
  )
}