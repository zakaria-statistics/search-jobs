# Sequence Diagram — Full Pipeline (`cmd_run`)

Read top-to-bottom. Each arrow shows a method call and its return value.
Indentation shows nesting depth. External calls (network/disk) are marked with `*`.

```
 User                pipeline.py              scraper/                  ranker/                     External
  │                      │                       │                        │                            │
  │  python pipeline.py run                      │                        │                            │
  │─────────────────────>│                       │                        │                            │
  │                      │                       │                        │                            │
  │                      │ _create_run_dir()      │                        │                            │
  │                      │──┐ mkdir output/runs/{ts}/                      │                            │
  │                      │<─┘ run_dir             │                        │                            │
  │                      │                       │                        │                            │
  │                 [1/6] SCRAPE                  │                        │                            │
  │                      │                       │                        │                            │
  │                      │ cmd_scrape(args)       │                        │                            │
  │                      │──────────────────────>│                        │                            │
  │                      │                       │                        │                            │
  │                      │  for src in [indeed, remoteok, arbeitnow, rekrute, wttj]:                   │
  │                      │                       │                        │                            │
  │                      │    scraper_map[src]()  │                        │                            │
  │                      │──────────────────────>│ __init__()             │                            │
  │                      │                       │                        │                            │
  │                      │    scraper.scrape(kw, regions, max_pages)      │                            │
  │                      │──────────────────────>│                        │                            │
  │                      │                       │  *HTTP/headless ──────────────────────────────────>│ Job sites
  │                      │                       │  <── HTML/JSON ──────────────────────────────────<│
  │                      │                       │                        │                            │
  │                      │                       │  config.match_job(title, tags)                      │
  │                      │                       │──┐ 5-tier keyword matching                          │
  │                      │                       │<─┘ bool                │                            │
  │                      │                       │                        │                            │
  │                      │                       │  BaseScraper.dedup(jobs)                            │
  │                      │                       │──┐ deduplicate by URL  │                            │
  │                      │                       │<─┘ list[Job]           │                            │
  │                      │                       │                        │                            │
  │                      │  <── list[Job] ───────│                        │                            │
  │                      │                       │                        │                            │
  │                      │  storage.save_jobs(all_jobs, run_dir=run_dir)  │                            │
  │                      │──────────────────────>│                        │                            │
  │                      │                       │  *write scraped.json   │                            │
  │                      │  <── filepath ────────│                        │                            │
  │                      │                       │                        │                            │
  │                      │  storage.print_summary(all_jobs)               │                            │
  │                      │──────────────────────>│                        │                            │
  │                      │                       │                        │                            │
  │                 [2/6] ENRICH                  │                        │                            │
  │                      │                       │                        │                            │
  │                      │ cmd_enrich(args)       │                        │                            │
  │                      │──┐ _find_latest_file("scraped_")               │                            │
  │                      │<─┘ filepath            │                        │                            │
  │                      │                       │                        │                            │
  │                      │  IndeedScraper()       │                        │                            │
  │                      │──────────────────────>│                        │                            │
  │                      │  scraper.enrich(jobs, max_jobs=50)             │                            │
  │                      │──────────────────────>│                        │                            │
  │                      │                       │  for job in indeed_jobs[:50]:                        │
  │                      │                       │    *StealthyFetcher.fetch(job.url) ───────────────>│ Indeed
  │                      │                       │    <── HTML ──────────────────────────────────────<│
  │                      │                       │    description_utils.extract_skill_sentences(html)  │
  │                      │                       │──┐ NLP-lite extraction │                            │
  │                      │                       │<─┘ skill_text          │                            │
  │                      │                       │    job["description"] = skill_text  (in-place)      │
  │                      │                       │                        │                            │
  │                      │  *write scraped.json (updated in-place)        │                            │
  │                      │                       │                        │                            │
  │                 [3/6] FILTER                  │                        │                            │
  │                      │                       │                        │                            │
  │                      │ cmd_filter(args)       │                        │                            │
  │                      │──┐ _find_latest_file("scraped_")               │                            │
  │                      │<─┘ filepath            │                        │                            │
  │                      │                       │                        │                            │
  │                      │  rank.load_scraped_jobs(filepath)              │                            │
  │                      │──────────────────────────────────────────────>│                            │
  │                      │  <── list[dict] ─────────────────────────────│                            │
  │                      │                       │                        │                            │
  │                      │  semantic_filter.semantic_filter_jobs(jobs, threshold)                      │
  │                      │──────────────────────────────────────────────>│                            │
  │                      │                       │                        │                            │
  │                      │                       │  semantic_filter._ensure_index()                    │
  │                      │                       │                       │──┐                          │
  │                      │                       │                       │  │ vectorstore.full_index()  │
  │                      │                       │                       │  │──┐                       │
  │                      │                       │                       │  │  │ needs_reindex() → hash check
  │                      │                       │                       │  │  │ init_collection()     │
  │                      │                       │                       │  │  │   *chromadb.PersistentClient()
  │                      │                       │                       │  │  │ index_resumes() → chunk_markdown() + upsert
  │                      │                       │                       │  │  │ index_candidate_context() → chunk + upsert
  │                      │                       │                       │  │<─┘ total_chunks          │
  │                      │                       │                       │  │                          │
  │                      │                       │                       │  │ vectorstore.init_collection()
  │                      │                       │                       │<─┘ collection               │
  │                      │                       │                        │                            │
  │                      │                       │  for each job:         │                            │
  │                      │                       │                        │                            │
  │                      │                       │    vectorstore.query_jobs(collection, title+desc, n=5)
  │                      │                       │                       │──┐                          │
  │                      │                       │                       │  │ collection.query()        │
  │                      │                       │                       │  │ distance → similarity = 1-(d/2)
  │                      │                       │                       │<─┘ list[{text, similarity, metadata}]
  │                      │                       │                        │                            │
  │                      │                       │    if best_similarity < threshold → DROP            │
  │                      │                       │                        │                            │
  │                      │                       │    composite_score.compute_composite_score(job)     │
  │                      │                       │                       │──┐                          │
  │                      │                       │                       │  │ _skill_match_score()      │
  │                      │                       │                       │  │ _title_match_score()      │
  │                      │                       │                       │  │ _location_match_score()   │
  │                      │                       │                       │  │ _stack_depth_score()      │
  │                      │                       │                       │  │ Σ(weight × signal)        │
  │                      │                       │                       │<─┘ {composite_score, score_breakdown}
  │                      │                       │                        │                            │
  │                      │                       │    job += semantic_score, matched_stack,            │
  │                      │                       │           relevant_chunks, composite_score,         │
  │                      │                       │           score_breakdown                           │
  │                      │                       │                        │                            │
  │                      │  <── filtered (sorted by composite_score desc)│                            │
  │                      │                       │                        │                            │
  │                      │  _bucket_jobs(filtered)│                        │                            │
  │                      │──┐ top (≥0.75), strong (0.60-0.75), moderate (0.45-0.60)                    │
  │                      │<─┘ buckets             │                        │                            │
  │                      │                       │                        │                            │
  │                      │  *write filtered_top.json, filtered_strong.json, filtered_moderate.json     │
  │                      │                       │                        │                            │
  │                 [4/6] PREPARE                 │                        │                            │
  │                      │                       │                        │                            │
  │                      │ cmd_prepare(args)      │                        │                            │
  │                      │──┐ _find_latest_file("filtered_top_")          │                            │
  │                      │<─┘ filepath            │                        │                            │
  │                      │                       │                        │                            │
  │                      │  rank.load_scraped_jobs(filepath)              │                            │
  │                      │──────────────────────────────────────────────>│                            │
  │                      │  <── list[dict] ─────────────────────────────│                            │
  │                      │                       │                        │                            │
  │                      │  rank.prepare_jobs(jobs)                       │                            │
  │                      │──────────────────────────────────────────────>│                            │
  │                      │                       │                        │                            │
  │                      │                       │  for each job:         │                            │
  │                      │                       │    rank.slim_job(job)  │                            │
  │                      │                       │                       │──┐                          │
  │                      │                       │                       │  │ keep JOB_FIELDS_FOR_RANKING
  │                      │                       │                       │  │ extract_skill_sentences(desc) if long
  │                      │                       │                       │  │ semantic_filter.get_rag_context(job)
  │                      │                       │                       │  │   → format relevant_chunks as text
  │                      │                       │                       │  │ attach: resume_context, semantic_score,
  │                      │                       │                       │  │         matched_stack
  │                      │                       │                       │<─┘ slim_dict (~12 fields)   │
  │                      │                       │                        │                            │
  │                      │  <── list[slim_dict] ────────────────────────│                            │
  │                      │                       │                        │                            │
  │                      │  *write prepared.json  │                        │                            │
  │                      │  print: job count, payload chars, token est, fields, RAG coverage          │
  │                      │                       │                        │                            │
  │                 [5/6] RANK                    │                        │                            │
  │                      │                       │                        │                            │
  │                      │ cmd_rank(args)         │                        │                            │
  │                      │──┐ _find_latest_file("prepared_")              │                            │
  │                      │<─┘ filepath            │                        │                            │
  │                      │                       │                        │                            │
  │                      │  rank.load_scraped_jobs(filepath)              │                            │
  │                      │──────────────────────────────────────────────>│                            │
  │                      │                       │                        │                            │
  │                      │  rank.rank_jobs(jobs, skip_filter=True, prepared=True)                     │
  │                      │──────────────────────────────────────────────>│                            │
  │                      │                       │                        │                            │
  │                      │                       │  anthropic.Anthropic(api_key)                       │
  │                      │                       │                       │──┐ client                   │
  │                      │                       │                       │<─┘                          │
  │                      │                       │                        │                            │
  │                      │                       │  split into batches of 30                           │
  │                      │                       │                        │                            │
  │                      │                       │  for each batch:       │                            │
  │                      │                       │    _call_claude(client, batch, target_role)         │
  │                      │                       │                       │──┐                          │
  │                      │                       │                       │  │ json.dumps(batch)         │
  │                      │                       │                       │  │ *client.messages.stream()─────────>│ Anthropic API
  │                      │                       │                       │  │   system = SYSTEM_PROMPT_JOBS      │
  │                      │                       │                       │  │   messages = [{user: jobs_json}]   │
  │                      │                       │                       │  │                          │        │
  │                      │                       │                       │  │   for text in stream:    │        │
  │                      │                       │                       │  │     <── token chunks ────────────<│
  │                      │                       │                       │  │     collect + progress   │        │
  │                      │                       │                       │  │                          │        │
  │                      │                       │                       │  │ json.loads(collected)    │        │
  │                      │                       │                       │<─┘ {ranked_jobs, global_insights}    │
  │                      │                       │                        │                            │
  │                      │                       │  if multiple batches:  │                            │
  │                      │                       │    _merge_results(batch_results)                    │
  │                      │                       │                       │──┐                          │
  │                      │                       │                       │  │ combine ranked_jobs       │
  │                      │                       │                       │  │ re-sort by overall score  │
  │                      │                       │                       │  │ re-number ranks 1..N      │
  │                      │                       │                       │  │ deduplicate insights      │
  │                      │                       │                       │  │ compute merged summary    │
  │                      │                       │                       │<─┘ merged result            │
  │                      │                       │                        │                            │
  │                      │  <── {search_summary, ranked_jobs, global_insights}                        │
  │                      │                       │                        │                            │
  │                      │  rank.save_ranked(ranked, run_dir=run_dir)     │                            │
  │                      │──────────────────────────────────────────────>│                            │
  │                      │                       │  *write ranked.json    │                            │
  │                      │  <── filepath ───────────────────────────────│                            │
  │                      │                       │                        │                            │
  │                 [6/6] REVIEW                  │                        │                            │
  │                      │                       │                        │                            │
  │                      │ cmd_review(args)       │                        │                            │
  │                      │──┐ _find_latest_file("ranked_")                │                            │
  │                      │<─┘ filepath            │                        │                            │
  │                      │                       │                        │                            │
  │                      │  *read ranked.json     │                        │                            │
  │                      │  group by priority: apply_now → strong_match → worth_trying → long_shot    │
  │                      │                       │                        │                            │
  │                      │  for each job:         │                        │                            │
  │  <── show: score, title, company, skills     │                        │                            │
  │                      │                       │                        │                            │
  │  [a]pprove ─────────>│                       │                        │                            │
  │                      │  _import_job_to_tracker(job)                   │                            │
  │                      │──┐ *read opportunities.json                    │                            │
  │                      │  │  check URL dedup    │                        │                            │
  │                      │  │  build opportunity{id, role, company, status, scores, ...}               │
  │                      │  │  *write opportunities.json                  │                            │
  │                      │<─┘ "Imported as #N"    │                        │                            │
  │                      │                       │                        │                            │
  │  [s]kip ────────────>│  skipped++             │                        │                            │
  │  [v]iew ────────────>│  show: url, source, resume_tweaks             │                            │
  │  [q]uit ────────────>│  print summary (approved, skipped)            │                            │
  │                      │                       │                        │                            │
  │  <── "Review complete. Approved: N, Skipped: M"                      │                            │
  │                      │                       │                        │                            │
```

## Standalone Commands (not part of `cmd_run`)

```
 User                pipeline.py              ranker/                     External
  │                      │                       │                          │
  │  pipeline.py index [--force]                 │                          │
  │─────────────────────>│                       │                          │
  │                      │  vectorstore.full_index(chromadb_dir, resumes_dir, ...)                    │
  │                      │──────────────────────>│                          │
  │                      │                       │  needs_reindex() → MD5 hash comparison             │
  │                      │                       │  init_collection() → *PersistentClient()           │
  │                      │                       │  index_resumes() → chunk_markdown(## headings)     │
  │                      │                       │    → collection.upsert(ids, docs, metadatas)       │
  │                      │                       │  index_candidate_context() → chunk(### headings)   │
  │                      │                       │    → collection.upsert(ids, docs, metadatas)       │
  │                      │                       │  _save_index_hash()     │                          │
  │                      │  <── total_chunks ────│                          │                          │
  │                      │                       │                          │
  │  pipeline.py status  │                       │                          │
  │─────────────────────>│                       │                          │
  │                      │  *glob runs/*/scraped.json → count + stats                                │
  │                      │  *glob runs/*/ranked.json  → count + stats                                │
  │                      │  *read opportunities.json  → group by status                              │
  │                      │  *read contacts.json       → count                                        │
  │  <── formatted stats │                       │                          │
  │                      │                       │                          │
  │  pipeline.py manual  │                       │                          │
  │─────────────────────>│                       │                          │
  │                      │  subprocess.run(opportunity_tracker.py add)                                │
  │  <── interactive prompts (company, role, location, url, notes)                                    │
  │  ──> user input ────>│  *write opportunities.json                      │                          │
  │                      │                       │                          │
```
