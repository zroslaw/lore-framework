export const meta = {
  name: 'df-ula-file-pass',
  description: 'ULA single-file pass. Split a file into units, then per unit (in parallel) run one agent through three ordered steps: A find bugs -> B generate clean-room scenarios -> C gap-analyze against existing tests. Returns schema-validated {bugs, scenarios, gap} per unit; the calling skill persists the YAML.',
  phases: [
    { title: 'Split',     detail: 'splitter agent breaks the file into testable units (id + signature)' },
    { title: 'Unit Pass', detail: 'one agent per unit (parallel) runs A->B->C sequentially' },
  ],
}

// args (kept small — the file is NOT passed in; agents read it themselves off disk):
//   filePath: string                      — repo-relative path of the target file
//   language: string                      — e.g. "swift"
//   sourceRepoPath: string                — absolute path; agents read the file + neighbours/tests from here
//   prompts: { split, preamble, stepA, stepB, stepC, stepD, stepE }   — md text, injected by the skill
//   schemas: { units, bugs, scenarios, gap }            — parsed JSON Schema, injected by the skill
const {
  filePath,
  language,
  sourceRepoPath,
  prompts,
  schemas,
} = (typeof args === 'string' ? JSON.parse(args) : args) ?? {}

if (!filePath || !language || !sourceRepoPath || !prompts || !schemas) {
  throw new Error('args must include { filePath, language, sourceRepoPath, prompts, schemas }')
}

// Fail loud if any expected prompt/schema key is missing — otherwise the literal
// "undefined" gets embedded into an agent prompt (#1) or a malformed agent schema
// is built from an undefined sub-schema (#5).
// Strip the $schema meta-URL (draft-2020-12) before handing a schema to agent():
// the runtime's validator is draft-07-era and can't resolve that meta ref. Our schemas
// use only draft-07-compatible keywords, so they validate fine without it. ($schema
// stays in the .json files for editor tooling — we strip only at the agent() boundary.)
const noMeta = (s) => { const { $schema, ...rest } = s; return rest }

const REQUIRED_PROMPTS = ['split', 'preamble', 'stepA', 'stepB', 'stepC', 'stepD', 'stepE']
const REQUIRED_SCHEMAS = ['units', 'bugs', 'scenarios', 'gap']
const missingPrompts = REQUIRED_PROMPTS.filter(k => !prompts[k])
const missingSchemas = REQUIRED_SCHEMAS.filter(k => !schemas[k])
if (missingPrompts.length || missingSchemas.length) {
  throw new Error(`Missing injected inputs — prompts:[${missingPrompts}] schemas:[${missingSchemas}]. The skill must map prompt files and schema files to these exact keys (see df/aiqa/ula-file.md step 3).`)
}

const REPO_NOTE = `The source repository is at: ${sourceRepoPath}\nYou may read other files in it for context (callers, callees, types). Use your own judgement about how much context you need.`

// ─── Phase 1: Split ──────────────────────────────────────────────────────────

phase('Split')

const split = await agent(
  `${prompts.split}

${REPO_NOTE}

The file to split is \`${filePath}\` (relative to the source repo above). **Read it yourself** — the full file is intentionally not pasted here.`,
  { label: 'split', phase: 'Split', schema: noMeta(schemas.units) }
)

const units = split.units ?? []
log(`Split ${filePath} into ${units.length} unit(s): ${units.map(u => u.id).join(', ')}`)

// ─── Phase 2: Unit Pass (per unit, parallel; A->B->C sequential inside one agent) ──

phase('Unit Pass')

// One agent per unit. The agent runs steps A->B->C in order, communicating between
// steps only through the artifacts it produces. Returns all three artifacts at once.
// Splitting later = give stepA/stepB/stepC to three separate agents, unchanged.
const unitResultSchema = {
  type: 'object',
  required: ['bugs', 'scenarios', 'gap'],
  additionalProperties: false,
  properties: {
    bugs: noMeta(schemas.bugs),
    scenarios: noMeta(schemas.scenarios),
    gap: noMeta(schemas.gap),
  },
}

const results = await parallel(units.map(unit => () => agent(
  `${prompts.preamble}

Unit under analysis:
- slug: ${unit.id}
- signature: ${unit.signature}

${REPO_NOTE}

The file under analysis is \`${filePath}\` (relative to the source repo above). **Read it yourself** and locate this unit by its signature — the full file is intentionally not pasted here, so read only what you need.

═══════════════════════════════════════════════════════════════
STEP A — FIND BUGS
═══════════════════════════════════════════════════════════════
${prompts.stepA}

═══════════════════════════════════════════════════════════════
STEP B — GENERATE SCENARIOS (clean-room)
═══════════════════════════════════════════════════════════════
${prompts.stepB}

═══════════════════════════════════════════════════════════════
STEP C — GAP ANALYSIS
═══════════════════════════════════════════════════════════════
${prompts.stepC}

═══════════════════════════════════════════════════════════════
STEP D — VERIFY BUGS
═══════════════════════════════════════════════════════════════
${prompts.stepD}

═══════════════════════════════════════════════════════════════
STEP E — VERIFICATION GUARDRAIL
═══════════════════════════════════════════════════════════════
${prompts.stepE}

═══════════════════════════════════════════════════════════════
Return one object: { "bugs": <bugs.yaml>, "scenarios": <scenarios.yaml>, "gap": <gap.yaml> }.
Each value must conform to its artifact schema. Use unit slug "${unit.id}" and the signature above in every artifact's header.`,
  { label: `unit-pass:${unit.id}`, phase: 'Unit Pass', schema: unitResultSchema }
)))

// Match each result back to its unit by the artifact's OWN slug — do not assume
// parallel() preserves input order (#2). Each artifact already carries its own
// unit/signature header, so we key off that rather than zipping by index.
const byUnit = new Map()
for (const r of results) {
  if (r && r.bugs && r.scenarios && r.gap) byUnit.set(r.bugs.unit, r)
}

const cleanResults = []
const dropped = []
for (const unit of units) {
  const r = byUnit.get(unit.id)
  if (r) cleanResults.push(r)
  else dropped.push(unit.id)   // name dropped units rather than losing them silently (#3)
}

if (dropped.length) {
  log(`WARNING: ${dropped.length}/${units.length} unit(s) produced no usable result and were dropped: ${dropped.join(', ')}`)
}
log(`Completed ${cleanResults.length}/${units.length} unit pass(es)`)

return {
  filePath,
  language,
  units: units.length,
  dropped,                 // unit slugs that produced no usable result — surface to the user
  results: cleanResults,   // [{ bugs, scenarios, gap }] — each carries its own unit/signature header; the skill aggregates these into per-file artifacts (provenance header + units[])
}
