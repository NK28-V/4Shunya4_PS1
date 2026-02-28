"use client"

import React from "react"
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
} from "reactflow"
import "reactflow/dist/style.css"

import { useComplianceGraph } from "@/app/hooks/useComplianceGraph"

interface DataFlowEdge {
  from: string
  to: string
  encrypted: boolean
  containsPII?: boolean
}

interface ComplianceFlowProps {
  dataFlow: DataFlowEdge[]
}

export default function ComplianceFlow({
  dataFlow,
}: ComplianceFlowProps) {
  const { nodes, edges } = useComplianceGraph(dataFlow)

  return (
    <div className="w-full h-[500px] bg-[#0B0B0C] border border-zinc-800 rounded-md">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
      >
        <MiniMap
          nodeColor={(node) =>
            node.className === "gdpr-violation"
              ? "#E10600"
              : "#16a34a"
          }
        />
        <Controls />
        <Background color="#222" gap={20} />
      </ReactFlow>
    </div>
  )
}