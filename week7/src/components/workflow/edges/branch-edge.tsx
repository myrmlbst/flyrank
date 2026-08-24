import {
  BaseEdge,
  EdgeLabelRenderer,
  getSmoothStepPath,
  type EdgeProps,
} from "@xyflow/react";
import { cn } from "@/lib/utils";
import type { BranchEdge as BranchEdgeType } from "../types";

const BRANCH_STYLES = {
  yes: { stroke: "var(--color-emerald-600)", text: "text-emerald-600" },
  no: { stroke: "var(--color-destructive)", text: "text-destructive" },
} as const;

function BranchEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  markerEnd,
  style,
  branch,
}: EdgeProps<BranchEdgeType> & { branch: "yes" | "no" }) {
  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
  });
  const { stroke, text } = BRANCH_STYLES[branch];

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        style={{ stroke, strokeWidth: 2, ...style }}
      />
      <EdgeLabelRenderer>
        <div
          className={cn(
            "nodrag nopan absolute rounded bg-background px-1.5 py-0.5 text-[10px] font-semibold shadow-sm ring-1 ring-foreground/10",
            text,
          )}
          style={{
            transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
          }}
        >
          {branch.toUpperCase()}
        </div>
      </EdgeLabelRenderer>
    </>
  );
}

export function YesEdge(props: EdgeProps<BranchEdgeType>) {
  return <BranchEdge {...props} branch="yes" />;
}

export function NoEdge(props: EdgeProps<BranchEdgeType>) {
  return <BranchEdge {...props} branch="no" />;
}

export const edgeTypes = {
  yes: YesEdge,
  no: NoEdge,
};
