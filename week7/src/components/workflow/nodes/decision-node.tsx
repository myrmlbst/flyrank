import { Handle, Position, useReactFlow, type NodeProps } from "@xyflow/react";
import { Split } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import type { DecisionNode } from "../types";

export function DecisionNodeComponent({ id, data }: NodeProps<DecisionNode>) {
  const { updateNodeData } = useReactFlow();

  return (
    <Card className="relative w-64 gap-2 overflow-visible border-t-4 border-t-primary py-3 shadow-sm transition-shadow hover:shadow-md">
      <Handle
        type="target"
        position={Position.Top}
        className="h-2.5! w-2.5! border-2! border-background! bg-foreground! transition-transform hover:scale-125"
      />
      <CardHeader className="flex flex-row items-center gap-1.5 px-3">
        <Split className="size-3.5 text-primary" />
        <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {data.label}
        </span>
      </CardHeader>
      <CardContent className="px-3">
        <Textarea
          className="nodrag nowheel min-h-16 resize-none text-sm"
          placeholder="What should this step ask the model?"
          value={data.prompt}
          onChange={(event) =>
            updateNodeData(id, { prompt: event.target.value })
          }
        />
      </CardContent>

      <Handle
        id="no"
        type="source"
        position={Position.Bottom}
        style={{ left: "25%" }}
        className="h-2.5! w-2.5! border-2! border-background! bg-destructive! transition-transform hover:scale-125"
      />
      <span className="pointer-events-none absolute -bottom-5 left-[25%] -translate-x-1/2 text-[10px] font-semibold text-destructive">
        NO
      </span>

      <Handle
        id="yes"
        type="source"
        position={Position.Bottom}
        style={{ left: "75%" }}
        className="h-2.5! w-2.5! border-2! border-background! bg-emerald-600! transition-transform hover:scale-125"
      />
      <span className="pointer-events-none absolute -bottom-5 left-[75%] -translate-x-1/2 text-[10px] font-semibold text-emerald-600">
        YES
      </span>
    </Card>
  );
}
