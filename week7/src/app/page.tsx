import { Badge } from "@/components/ui/badge";
import { WorkflowCanvas } from "@/components/workflow/workflow-canvas";

export default function Home() {
  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6 px-6 py-10">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">
          AI Workflow Visualizer
        </h1>
        <Badge variant="secondary">Phase 1: Setup</Badge>
      </div>
      <p className="max-w-2xl text-muted-foreground">
        Each node in the graph below represents an AI decision step that
        resolves to YES or NO. Execution will run through Inngest; this
        canvas is the React Flow scaffold the real workflow will render into.
      </p>
      <WorkflowCanvas />
    </div>
  );
}
