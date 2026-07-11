// Minimal live probe of the H TS SDK to see the real call shape + timing.
import { HaiAgentsClient } from "hai-agents";
import { z } from "zod";

const mod = await import("hai-agents");
console.log("hai-agents exports:", Object.keys(mod));

const client = new HaiAgentsClient();
console.log("client methods:", Object.getOwnPropertyNames(Object.getPrototypeOf(client)).filter((m) => m !== "constructor"));

const Schema = z.object({ h1: z.string() });

const t0 = Date.now();
try {
  console.log("starting runSession (simple task)…");
  const result = await client.runSession({
    agent: "h/web-surfer-flash",
    messages: "Go to https://example.com and return the exact text of the H1 heading on the page.",
    answerSchema: Schema,
  });
  console.log("elapsed:", ((Date.now() - t0) / 1000).toFixed(1) + "s");
  console.log("result keys:", result && Object.keys(result));
  console.log("status:", result?.status);
  console.log("answer:", JSON.stringify(result?.answer));
} catch (e) {
  console.log("elapsed:", ((Date.now() - t0) / 1000).toFixed(1) + "s");
  console.error("ERROR:", e?.name, e?.message);
  if (e?.response) console.error("response:", JSON.stringify(e.response).slice(0, 500));
  console.error(e?.stack?.split("\n").slice(0, 4).join("\n"));
}
