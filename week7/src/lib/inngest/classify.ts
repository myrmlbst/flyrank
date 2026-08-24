import OpenAI from "openai";

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

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
 */
export async function classifyYesNo(prompt: string): Promise<YesNo> {
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
