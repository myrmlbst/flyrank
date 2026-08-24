import { Handle, Position, type NodeProps } from "@xyflow/react";
import { Card, CardContent } from "@/components/ui/card";
import type { OutcomeNode } from "../types";

export function OutcomeNodeComponent({ data }: NodeProps<OutcomeNode>) {
  return (
    <Card className="w-48 gap-0 border-dashed py-3 shadow-sm">
      <Handle
        type="target"
        position={Position.Top}
        className="h-2.5! w-2.5! border-2! border-background! bg-muted-foreground!"
      />
      <CardContent className="px-3 text-center text-sm font-medium">
        {data.label}
      </CardContent>
    </Card>
  );
}
