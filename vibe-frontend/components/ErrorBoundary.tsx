"use client"

import React from "react"

interface State {
  hasError: boolean
}

export default class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  State
> {
  constructor(props: any) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error: any, info: any) {
    console.error("ErrorBoundary caught:", error, info)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-[#0B0B0C] text-white">
          <div className="text-center">
            <h2 className="text-xl font-bold text-red-500 mb-4">
              Dashboard Recovery Mode
            </h2>
            <p className="text-zinc-400 text-sm">
              An unexpected error occurred while rendering this scan.
              The system remains stable.
            </p>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}