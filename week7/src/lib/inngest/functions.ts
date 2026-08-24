import OpenAI from "openai";
import { inngest } from "./client";

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

// Smoke-test function: proves the Inngest dev server, event flow, and OpenAI
// SDK are wired together end to end. Real decision-node functions land in a
// later phase.
export const decisionStep = inngest.createFunction(
  { id: "decision-step", triggers: { event: "workflow/decision.requested" } },
  async ({ event, step }) => {
    const answer = await step.run("ask-openai", async () => {
      const completion = await openai.chat.completions.create({
        model: "gpt-4o-mini",
        messages: [
          {
            role: "system",
            content:
              "You are a decision node in a workflow graph. Answer with exactly one word: YES or NO.",
          },
          { role: "user", content: event.data.question },
        ],
      });

      return completion.choices[0]?.message?.content?.trim() ?? "NO";
    });

    return { question: event.data.question, answer };
  },
);
