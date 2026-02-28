import { useMemo } from "react"
import { Node, Edge } from "reactflow"

interface DataFlowEdge {
  from: string
  to: string
  encrypted: boolean
  containsPII?: boolean
}

interface UseComplianceGraphReturn {
  nodes: Node[]
  edges: Edge[]
}

export function useComplianceGraph(
  dataFlow: DataFlowEdge[]
): UseComplianceGraphReturn {

  return useMemo(() => {
    const nodeSet = new Set<string>()

    dataFlow.forEach(edge => {
      nodeSet.add(edge.from)
      nodeSet.add(edge.to)
    })

    const nodes: Node[] = Array.from(nodeSet).map((id, index) => {
        const xPosition = 100 + index * 250
        const yPosition = 200
      
        const isViolation = dataFlow.some(
          edge =>
            edge.to === id &&
            edge.containsPII &&
            !edge.encrypted
        )
      
        return {
          id,
          position: { x: xPosition, y: yPosition },
          data: { label: id },
          className: isViolation ? "gdpr-violation" : "",
          style: {
            border: isViolation
              ? "2px solid #E10600"
              : "1px solid #333",
            background: "#111",
            color: "#fff",
            padding: 12,
            borderRadius: 8,
            minWidth: 140,
            textAlign: "center"
          }
        }
      })
    const edges: Edge[] = dataFlow.map((edge, index) => ({
      id: `e-${index}`,
      source: edge.from,
      target: edge.to,
      animated: false,
      style: {
        stroke: edge.encrypted ? "#16a34a" : "#E10600",
        strokeWidth: 2,
        strokeDasharray: edge.encrypted ? "0" : "5,5"
      }
    }))

    return { nodes, edges }
  }, [dataFlow])
}