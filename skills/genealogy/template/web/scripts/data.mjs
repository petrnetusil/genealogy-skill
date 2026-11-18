// `npm run data`: runs ../tools/export_web.py with the first working Python 3.
// macOS/Linux: python3; Windows: python or py -3 ("python3" there is often only a non-working Microsoft Store alias).
// -X utf8: with -I the PYTHONUTF8 variable is ignored; on Windows the output and files would otherwise be in cp1250.
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const script = fileURLToPath(new URL("../../tools/export_web.py", import.meta.url));
const candidates = process.platform === "win32"
  ? [["python"], ["py", "-3"], ["python3"]]
  : [["python3"], ["python"]];

for (const [cmd, ...pre] of candidates) {
  const probe = spawnSync(cmd, [...pre, "-c", "import sys; sys.exit(sys.version_info < (3, 9))"], { stdio: "ignore" });
  if (probe.status !== 0) continue;
  const run = spawnSync(cmd, [...pre, "-I", "-X", "utf8", script, ...process.argv.slice(2)], { stdio: "inherit" });
  process.exit(run.status ?? 1);
}
console.error("Python 3.9+ not found (python3, python or py -3). Install it (python.org) and try again.");
process.exit(1);
