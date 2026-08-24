import { Handle, Position, type NodeProps } from "@xyflow/react";
import { Flag } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import type { OutcomeNode } from "../types";

export function OutcomeNodeComponent({ data }: NodeProps<OutcomeNode>) {
  return (
    <Card className="w-48 gap-0 border-l-4 border-l-primary/50 bg-muted/30 py-3 shadow-sm transition-shadow hover:shadow-md">
      <Handle
        type="target"
        position={Position.Top}
        className="h-2.5! w-2.5! border-2! border-background! bg-muted-foreground! transition-transform hover:scale-125"
      />
      <CardContent className="flex items-center justify-center gap-1.5 px-3 text-center text-sm font-medium">
        <Flag className="size-3.5 shrink-0 text-primary" />
        {data.label}
      </CardContent>
    </Card>
  );
}
