import React from "react";
import { ScanReport } from "@/lib/types";

interface VibeScorecardProps {
  data: ScanReport;
}

type IndicatorColors = "green" | "yellow" | "red";

function getCodeCoverageColor(value: number): IndicatorColors {
  if (value >= 90) return "green";
  if (value >= 75) return "yellow";
  return "red";
}

function getCriticalIssuesColor(issues: number): IndicatorColors {
  if (issues === 0) return "green";
  if (issues <= 2) return "yellow";
  return "red";
}

function getAlertingColor(configured: boolean): IndicatorColors {
  return configured ? "green" : "red";
}

function getAvailabilityColor(value: number): IndicatorColors {
  if (value >= 99) return "green";
  if (value >= 95) return "yellow";
  return "red";
}

const colorClasses: Record<IndicatorColors, string> = {
  green: "text-green-400 border-green-500",
  yellow: "text-yellow-300 border-yellow-400",
  red: "text-red-500 border-red-500"
};

const bgClasses: Record<IndicatorColors, string> = {
    green: "bg-zinc-950",
    yellow: "bg-zinc-950",
    red: "bg-zinc-950"
  };
function Indicator({
  label,
  value,
  color,
  description,
}: {
  label: string;
  value: React.ReactNode;
  color: IndicatorColors;
  description?: string;
}) {
  return (
    <div
      className={`flex flex-col justify-between h-fullborder rounded-md p-5 min-h-[108px] ${colorClasses[color]} ${bgClasses[color]} shadow`}
    >
      <div className="flex justify-between items-center">
        <span className="text-xs tracking-wide text-zinc-400 uppercase">
          {label}
        </span>
        <span
          className={`w-2 h-2 rounded-full ml-2 ${
            color === "green"
              ? "bg-green-400"
              : color === "yellow"
              ? "bg-yellow-300"
              : "bg-red-500"
          } shadow`}
          title={color.charAt(0).toUpperCase() + color.slice(1)}
        />
      </div>
      <div className="mt-6 flex items-center gap-3">
        <span className={`text-2xl md:text-3xl font-bold ${colorClasses[color]}`}>
          {value}
        </span>
        {description && (
          <span className="text-xs text-zinc-400">{description}</span>
        )}
      </div>
    </div>
  );
}

const VibeScorecard: React.FC<VibeScorecardProps> = ({ data }) => {
  const codeCoverageColor = getCodeCoverageColor(data.codeCoverage);
  const criticalIssuesColor = getCriticalIssuesColor(data.criticalIssues);
  const alertingColor = getAlertingColor(data.alertingConfigured);
  const availabilityColor = getAvailabilityColor(data.availabilitySLO);

  return (
    <section className="mt-14 px-2">
      <div
        className="grid grid-cols-1 xs:grid-cols-2 sm:grid-cols-2 md:grid-cols-4 gap-6"
      >
        <Indicator
          label="Code Coverage"
          value={`${data.codeCoverage}%`}
          description="Target > 90%"
          color={codeCoverageColor}
        />
        <Indicator
          label="Critical Issues"
          value={data.criticalIssues}
          description="0 is ideal"
          color={criticalIssuesColor}
        />
        <Indicator
          label="Alerting"
          value={data.alertingConfigured ? "Enabled" : "Missing"}
          description="Must be configured"
          color={alertingColor}
        />
        <Indicator
          label="Availability SLO"
          value={`${data.availabilitySLO}%`}
          description="Target > 99%"
          color={availabilityColor}
        />
      </div>
    </section>
  );
};

export default VibeScorecard;