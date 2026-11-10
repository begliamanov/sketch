/**
 * Sketch for Pi.
 *
 * /sketch-sync          copy sketch's skills and agents into ~/.pi/agent/, filling in the placeholders
 * /sketch-sync remove   delete everything /sketch-sync copied
 *
 * Source: core/ and adapters/pi/agents.list in the package this file lives in.
 * Target: ~/.pi/agent/agents/, ~/.pi/agent/skills/ and ~/.pi/agent/sketch/core/.
 * ~/.pi/agent/sketch/manifest.json lists every file written, so a later sync or remove
 * only touches files it created.
 */
import { existsSync, mkdirSync, readdirSync, readFileSync, rmdirSync, rmSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const REPO = resolve(dirname(fileURLToPath(import.meta.url)), "../../..");
const CORE_SRC = join(REPO, "core");
const LIST = join(REPO, "adapters", "pi", "agents.list");

const AGENT_DIR = join(homedir(), ".pi", "agent");
const AGENTS_OUT = join(AGENT_DIR, "agents");
const SKILLS_OUT = join(AGENT_DIR, "skills");
const SKETCH_OUT = join(AGENT_DIR, "sketch");
const CORE_OUT = join(SKETCH_OUT, "core");
const MANIFEST = join(SKETCH_OUT, "manifest.json");

type Manifest = { version: string; files: string[] };
type AgentEntry = { tools: string; model: string };

function listMarkdown(dir: string): string[] {
  const found: string[] = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) found.push(...listMarkdown(full));
    else if (entry.name.endsWith(".md")) found.push(full);
  }
  return found;
}

function readAgentList(): Map<string, AgentEntry> {
  const agents = new Map<string, AgentEntry>();
  for (const line of readFileSync(LIST, "utf8").split("\n")) {
    if (line.trim() === "" || line.startsWith("#")) continue;
    const [name, tools, model] = line.split("|");
    if (!name || !tools || !model) throw new Error(`agents.list: bad line '${line}'. Expected name|tools|model.`);
    agents.set(name.trim(), { tools: tools.trim(), model: model.trim() });
  }
  return agents;
}

/** Fill in the placeholders and adapt the text to Pi. */
function expand(text: string, skillCommands: string[], agent?: AgentEntry): string {
  // /tune-skills -> /skill:tune-skills. Whole words only, so paths such as .sketch/tasks or
  // .../agent/sketch/core are left alone. Done before the placeholders become paths.
  const commands = new RegExp(`(?<![\\w/.:-])/(${skillCommands.join("|")})(?![\\w/-])`, "g");
  let out = text
    .replace(commands, "/skill:$1")
    .replaceAll("{{CORE_SOURCE}}", CORE_SRC)
    .replaceAll("{{CORE}}", CORE_OUT)
    .replaceAll("{{VERSION}}", readFileSync(join(REPO, "VERSION"), "utf8").trim());
  // Pi appends a skill's arguments after the skill text
  out = out.replaceAll("$ARGUMENTS", "the text that follows these instructions in the user request");

  if (agent) {
    const lines = out.split("\n");
    const close = lines.indexOf("---", 1);
    if (lines[0] !== "---" || close === -1) throw new Error("an agent file has no frontmatter");
    const added = [`tools: ${agent.tools}`];
    if (agent.model !== "inherit") added.push(`model: ${agent.model}`);
    lines.splice(close, 0, ...added);
    out = lines.join("\n");
  }
  return out;
}

/** Everything sync will write: absolute path -> content. Reads only; writes nothing. */
function build(): { files: Map<string, string>; agents: number; skills: number; version: string } {
  const version = readFileSync(join(REPO, "VERSION"), "utf8").trim();
  const pkgVersion = JSON.parse(readFileSync(join(REPO, "package.json"), "utf8")).version;
  if (version !== pkgVersion) throw new Error(`VERSION is ${version} but package.json says ${pkgVersion}. Make them match.`);

  const agentList = readAgentList();
  const agentFiles = readdirSync(join(CORE_SRC, "agents")).filter((f) => f.endsWith(".md"));
  for (const file of agentFiles) {
    const name = file.slice(0, -3);
    if (!agentList.has(name)) throw new Error(`core/agents/${file} is not listed in adapters/pi/agents.list`);
  }
  for (const name of agentList.keys()) {
    if (!agentFiles.includes(`${name}.md`)) throw new Error(`agents.list names '${name}' but core/agents/${name}.md does not exist`);
  }

  const skillNames = readdirSync(join(CORE_SRC, "skills"), { withFileTypes: true })
    .filter((e) => e.isDirectory())
    .map((e) => e.name);
  for (const name of skillNames) {
    if (!existsSync(join(CORE_SRC, "skills", name, "SKILL.md"))) throw new Error(`core/skills/${name}/SKILL.md does not exist`);
  }

  const files = new Map<string, string>();
  for (const src of listMarkdown(CORE_SRC)) {
    files.set(join(CORE_OUT, relative(CORE_SRC, src)), expand(readFileSync(src, "utf8"), skillNames));
  }
  for (const [name, entry] of agentList) {
    files.set(join(AGENTS_OUT, `${name}.md`), expand(readFileSync(join(CORE_SRC, "agents", `${name}.md`), "utf8"), skillNames, entry));
  }
  for (const name of skillNames) {
    files.set(join(SKILLS_OUT, name, "SKILL.md"), expand(readFileSync(join(CORE_SRC, "skills", name, "SKILL.md"), "utf8"), skillNames));
  }
  return { files, agents: agentList.size, skills: skillNames.length, version };
}

function readManifest(): Manifest | undefined {
  return existsSync(MANIFEST) ? (JSON.parse(readFileSync(MANIFEST, "utf8")) as Manifest) : undefined;
}

/** Delete files, then any folders they leave empty (never the agents or skills folders themselves). */
function deleteFiles(paths: string[]): void {
  const keep = new Set([AGENT_DIR, AGENTS_OUT, SKILLS_OUT]);
  for (const path of paths) {
    rmSync(path, { force: true });
    let dir = dirname(path);
    while (!keep.has(dir) && existsSync(dir) && readdirSync(dir).length === 0) {
      rmdirSync(dir);
      dir = dirname(dir);
    }
  }
}

function sync(): string {
  const { files, agents, skills, version } = build();
  const old = readManifest();
  const owned = new Set(old?.files ?? []);

  // Stop before writing anything if a target is a file sketch did not create.
  const clashes = [...files.keys()].filter((path) => existsSync(path) && !owned.has(path));
  if (clashes.length > 0) {
    throw new Error(`these files already exist and were not created by sketch, so nothing was written:\n${clashes.join("\n")}`);
  }

  for (const [path, content] of files) {
    mkdirSync(dirname(path), { recursive: true });
    writeFileSync(path, content);
  }
  deleteFiles([...owned].filter((path) => !files.has(path)));

  mkdirSync(SKETCH_OUT, { recursive: true });
  const manifest: Manifest = { version, files: [...files.keys()].sort() };
  writeFileSync(MANIFEST, JSON.stringify(manifest, null, 2) + "\n");
  return `Synced sketch ${version}: ${agents} agents, ${skills} skills. Run /reload to pick them up.`;
}

function remove(): string {
  const manifest = readManifest();
  if (!manifest) throw new Error(`no manifest at ${MANIFEST}. Nothing to remove.`);
  deleteFiles(manifest.files);
  rmSync(MANIFEST, { force: true });
  if (existsSync(SKETCH_OUT) && readdirSync(SKETCH_OUT).length === 0) rmdirSync(SKETCH_OUT);
  return `Removed ${manifest.files.length} sketch files. Run /reload.`;
}

export default function (pi: ExtensionAPI) {
  pi.registerCommand("sketch-sync", {
    description: "Copy sketch's skills and agents into ~/.pi/agent (use 'remove' to delete them)",
    getArgumentCompletions: (prefix) => ["remove"].filter((s) => s.startsWith(prefix)).map((s) => ({ value: s, label: s })),
    handler: async (args, ctx) => {
      const mode = args.trim();
      try {
        if (mode !== "" && mode !== "remove") throw new Error(`unknown argument '${mode}'. Use /sketch-sync or /sketch-sync remove.`);
        ctx.ui.notify(mode === "remove" ? remove() : sync(), "info");
      } catch (error) {
        ctx.ui.notify(`STOPPED: ${error instanceof Error ? error.message : String(error)}`, "error");
      }
    },
  });
}
