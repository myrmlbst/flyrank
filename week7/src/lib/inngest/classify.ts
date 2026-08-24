import { NonRetriableError } from "inngest";
import OpenAI from "openai";

// A real timeout, and the SDK's own retries switched off -- step.run() in
// functions.ts already retries the whole call on failure, so leaving the
// SDK's default retries (2) on would silently stack on top of that and
// turn "a few attempts" into many more real HTTP calls than intended.
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
  timeout: 15_000,
  maxRetries: 0,
});

export type YesNo = "YES" | "NO";

/**
 * Sends a single decision-node prompt to the model and normalizes the reply
 * to exactly YES or NO -- the model is asked to answer with one word, but
 * nothing stops it from adding punctuation or extra text, so the response is
 * never trusted verbatim.
 *
 * OPENAI_STUB=1 skips the real API call and returns a deterministic answer
 * (hash of the prompt) so the Inngest step chain, graph traversal, and
 * frontend polling can all be exercised without an API key or spend.
 *
 * Throws on an empty prompt or an OpenAI/network failure -- callers run this
 * inside step.run(), so a thrown error becomes a retried (then eventually
 * failed) Inngest step rather than a silent wrong answer. An empty prompt
 * is permanent (retrying won't produce one), so it's raised as
 * NonRetriableError to fail the step immediately instead of burning
 * retries on something that can't change.
 */
export async function classifyYesNo(prompt: string): Promise<YesNo> {
  if (!prompt.trim()) {
    throw new NonRetriableError("Decision node prompt is empty");
  }

  if (process.env.OPENAI_STUB === "1") {
    let hash = 0;
    for (const char of prompt) hash = (hash * 31 + char.charCodeAt(0)) | 0;
    return Math.abs(hash) % 2 === 0 ? "YES" : "NO";
  }

  const completion = await openai.chat.completions.create({
    model: "gpt-4o-mini",
    messages: [
      {
        role: "system",
        content:
          "You are a decision node in a workflow graph. Answer with exactly one word: YES or NO.",
      },
      { role: "user", content: prompt },
    ],
  });

  const raw = completion.choices[0]?.message?.content?.trim().toUpperCase();
  return raw?.startsWith("Y") ? "YES" : "NO";
}
