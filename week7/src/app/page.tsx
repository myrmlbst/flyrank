import { Badge } from "@/components/ui/badge";
import { WorkflowCanvas } from "@/components/workflow/workflow-canvas";

export default function Home() {
  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6 px-6 py-10">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">
          AI Workflow Visualizer
        </h1>
        <Badge variant="secondary">Phase 4: End Product</Badge>
      </div>
      <p className="max-w-2xl text-muted-foreground">
        Each node is an AI decision step that resolves to YES or NO. Edit a
        node&apos;s prompt directly on the canvas, drag from a handle to wire
        up new connections, and add more decision nodes with the toolbar.
        The graph persists to your browser automatically.
      </p>
      <WorkflowCanvas />
    </div>
  );
}
