# Design Philosophy — Build Strategy

## Two Approaches

### Standalone Small Projects
- Explore/validate a single idea in isolation
- Feature has value on its own (a scraper, a scorer, a tracker)
- Fast iteration, no risk of breaking existing things
- Good for learning new techniques (vector DBs, embeddings, APIs)

### Monolith with Phases
- Features share data and state — output of one feeds the next
- Pipeline has a clear sequential flow
- One CLI, one config, one output structure
- Integration between parts IS the value

## The Hybrid Pattern (what this project does)

```
Phase 1: standalone scraper         (could live alone)
       ↓ output: scraped.json
Phase 2: added ranking              (needs scraper output)
       ↓ output: ranked.json
Phase 3: added vector DB            (needs resumes + scraper output)
       ↓ output: filtered.json + RAG context
Phase 4: composite scoring          (needs all of the above)
       ↓ output: scored + bucketed jobs
Phase 5: workflow glue              (ties everything together)
       ↓ output: runs/, trackers, review
```

Each phase was a buildable block that could have been a standalone experiment.
They composed into a pipeline because data flows naturally left-to-right.

## Rules

### 1. Prototype First, Promote Later
- New ideas start in `concepts/` or `experiments/` — single script, minimal dependencies
- Validate the idea works before wiring it into the pipeline
- Promote to a module when it proves useful AND needs upstream data

### 2. Loose Coupling Between Modules
- Each module reads files in, writes files out
- Modules communicate through JSON files, not direct function calls across boundaries
- Any module could be swapped without rewriting its neighbors
- Config is centralized but consumed independently

### 3. Data Flow Defines Structure
```
scraper/ --> output (JSON) --> ranker/ --> output (JSON) --> scripts/ (orchestrator)
```
- Upstream doesn't know about downstream
- Downstream discovers upstream output via file conventions
- Shared state (opportunities.json, contacts.json) lives outside the pipeline flow

### 4. Don't Architect What You Haven't Validated
- The scraper worked before ChromaDB existed
- The semantic filter worked before composite scoring existed
- Each phase validated its value before the next phase was designed
- Planning one phase ahead is enough — two phases ahead is speculation

### 5. Growth Pattern
```
Idea → Experiment (concepts/) → Standalone script → Pipeline module → Integrated feature
         ↑ kill here if                ↑ promote here if         ↑ refine here
         it doesn't work               it needs upstream data    once it's proven
```

## Anti-Patterns to Avoid

| Anti-Pattern | Why It Fails |
|---|---|
| Design full architecture before writing code | Requirements change once you see real data |
| Build "framework" before the second use case | Premature abstraction, wasted effort |
| Tight coupling between phases | Can't swap, test, or debug independently |
| Skip prototyping, go straight to production | No validation, higher cost of being wrong |
| Keep experiments in the main codebase forever | Clutter, confusion about what's active |

## How This Applies to New Features

When considering a new feature (e.g., "market trend analytics"):

1. **Ask:** Does it need existing pipeline data? → If no, build standalone first
2. **Ask:** Is the technique proven? → If no, prototype in `concepts/`
3. **Ask:** Does it change existing data flow? → If yes, plan carefully (G4+ change)
4. **Ask:** Can it be a new pipeline stage that reads existing output? → Best case, just append

Example path for "market trend analytics":
```
concepts/trend_analysis.py    → reads archived filtered_*.json, produces charts
                               → validate: are the trends meaningful?
scripts/pipeline.py trend     → promoted as new CLI command
                               → reads output/runs/*/filtered_*.json across runs
output/trends.json            → new persistent JSON DB tracking skill demand over time
```
