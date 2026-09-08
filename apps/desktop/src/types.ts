export interface ActiveContext {
  organization: string;
  repo: string;
  branch: string;
  taskKey: string;
  taskTitle: string;
  status: "ACTIVE" | "IN_PROGRESS" | "ANOMALY_DETECTED" | "COMPLETED";
  outgoingDev: {
    name: string;
    email?: string;
  };
  incomingDev: {
    name: string;
    email?: string;
  };
  executiveSummary?: string;
  activeArtifacts?: {
    id: string;
    type: string;
    title: string;
    status?: string;
    state?: string;
  }[];
}

export interface AnomalyAlert {
  id: string;
  ruleId: string;
  title: string;
  severity: "HIGH" | "MEDIUM" | "LOW" | "CRITICAL";
  description: string;
  action: string;
}

export interface ActionStep {
  id: number;
  title: string;
  description: string;
  targetFile?: string;
  completed: boolean;
}

export interface ChatMessage {
  id: string;
  sender: "user" | "kairo";
  content: string;
  citations?: string[];
  timestamp: string;
  dateStr?: string;
  dateDisplay?: string;
  createdAt?: number;
}
