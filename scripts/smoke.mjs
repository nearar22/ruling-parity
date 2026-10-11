import { createAccount, createClient } from "genlayer-js";
import { studioDevnet } from "genlayer-js/chains";

const contract = process.env.CONTRACT_ADDRESS?.trim();
const raw = process.env.GENLAYER_PRIVATE_KEY?.trim();
const rule = process.env.DEMO_RULE_URL?.trim();
const caseA = process.env.DEMO_CASE_A_URL?.trim();
const caseB = process.env.DEMO_CASE_B_URL?.trim();
if (!contract || !raw || !rule || !caseA || !caseB) throw new Error("Contract, key, rule URL, and two case URLs are required");
const key = raw.startsWith("0x") ? raw : `0x${raw}`;
const chain = { ...studioDevnet, id: 61997, name: "GenLayer Studio Next", rpcUrls: { default: { http: ["https://studio-next.genlayer.com/api"] } } };
const client = createClient({ chain, account: createAccount(key) });
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const id = `parity-demo-${Date.now().toString(36)}`;
async function finalized(hash) {
  for (let i = 0; i < 300; i++) {
    const receipt = await client.getTransaction({ hash }).catch(() => null);
    const status = String(receipt?.statusName ?? receipt?.status ?? "PENDING").toUpperCase();
    if (status === "FINALIZED") return receipt;
    if (["UNDETERMINED", "DECLINED", "CANCELED", "CANCELLED"].includes(status)) throw new Error(`Transaction ended ${status}`);
    await sleep(3000);
  }
  throw new Error("Transaction timed out");
}
async function write(label, functionName, args, intelligent = false) {
  const fees = await client.estimateTransactionFees({ leaderTimeunitsAllocation: intelligent ? 500n : 180n, validatorTimeunitsAllocation: intelligent ? 600n : 360n });
  const hash = await client.writeContract({ address: contract, functionName, args, fees });
  console.log(`${label}_TX=${hash}`);
  const receipt = await finalized(hash);
  if (String(receipt.statusName ?? receipt.status).toUpperCase() !== "FINALIZED" || String(receipt.txExecutionResultName ?? receipt.txExecutionResult) !== "FINISHED_WITH_RETURN") throw new Error(`${label} failed`);
}
await write("CREATE", "create_review", [id, "Local office decision parity", "Did two materially similar applications receive inconsistent outcomes under the same local-office rule?", rule, caseA, caseB]);
await write("EVALUATE", "evaluate", [id], true);
await write("FINALIZE", "finalize", [id]);
const state = await client.readContract({ address: contract, functionName: "get_review", args: [id], jsonSafeReturn: true });
console.log(`DEMO_REVIEW=${id}\nSTATE=${state.status}\nVERDICT=${state.evaluation?.verdict}\nSIMILARITY=${state.evaluation?.comparison?.similarity}`);
if (state.status !== "FINAL" || state.evaluation?.receipts?.length !== 3) throw new Error("Live smoke state is incomplete");
