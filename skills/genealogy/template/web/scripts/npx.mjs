// Runs `npx …` without a shell, so that arguments with spaces or quotes (a path "C:\Users\Jan Novak\…", JSON)
// arrive unchanged on Windows too. Node ships npx as the script npx-cli.js next to itself: on Windows
// <node.exe>\..\node_modules\npm\bin\npx-cli.js, elsewhere <bin>/../lib/node_modules/npm/bin/npx-cli.js.
// If it is not found (an unusual installation), we fall back to the shell (on Windows `npx.cmd`).
import { spawn, spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";

const bin = dirname(process.execPath);
const cli = [join(bin, "node_modules", "npm", "bin", "npx-cli.js"), join(bin, "..", "lib", "node_modules", "npm", "bin", "npx-cli.js")]
  .find((p) => existsSync(p));
const win = process.platform === "win32";

function command(args) {
  return cli ? [process.execPath, [cli, ...args], {}] : ["npx", args, { shell: win }];
}

export function npxSync(args, options = {}) {
  const [cmd, a, extra] = command(args);
  return spawnSync(cmd, a, { ...options, ...extra });
}

export function npxSpawn(args, options = {}) {
  const [cmd, a, extra] = command(args);
  return spawn(cmd, a, { ...options, ...extra });
}
