export interface DataFlowEdge {
    from: string
    to: string
    encrypted: boolean
    containsPII?: boolean
  }
  
  export interface ScanReport {
    id: string
    projectName: string
    score: number
    codeCoverage: number
    criticalIssues: number
    alertingConfigured: boolean
    availabilitySLO: number
    deploymentBlocked: boolean
    createdAt: string
    status: "PROCESSING" | "COMPLETED"
  
    vulnerabilities: {
      id: string
      file: string
      severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
      metadata: string[]
    }[]
  
    dataFlow: DataFlowEdge[]   // 👈 ADD THIS
  }