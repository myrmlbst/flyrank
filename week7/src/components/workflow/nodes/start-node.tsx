import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { StartNode } from "../types";

export function StartNodeComponent({ data }: NodeProps<StartNode>) {
  return (
    <div className="rounded-full border border-primary/30 bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-sm">
      {data.label}
      <Handle
        type="source"
        position={Position.Bottom}
        className="h-2.5! w-2.5! border-2! border-background! bg-primary!"
      />
    </div>
  );
}
