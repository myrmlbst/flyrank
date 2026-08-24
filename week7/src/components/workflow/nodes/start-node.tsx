import { Handle, Position, type NodeProps } from "@xyflow/react";
import { Play } from "lucide-react";
import type { StartNode } from "../types";

export function StartNodeComponent({ data }: NodeProps<StartNode>) {
  return (
    <div className="flex items-center gap-1.5 rounded-full border border-primary/30 bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-sm transition-shadow hover:shadow-md">
      <Play className="size-3.5 fill-current" />
      {data.label}
      <Handle
        type="source"
        position={Position.Bottom}
        className="h-2.5! w-2.5! border-2! border-background! bg-primary! transition-transform hover:scale-125"
      />
    </div>
  );
}
