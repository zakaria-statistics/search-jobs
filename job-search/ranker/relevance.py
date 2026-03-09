"""Relevance indicator — builds a summary block for any pipeline stage.

Answers: 'How many of these jobs are worth my time?'
Added to every stage's JSON output as the "relevance" key.
"""


def build_relevance(jobs: list[dict], stage: str) -> dict:
    """Build a relevance summary block for any pipeline stage."""
    total = len(jobs)
    if total == 0:
        return {"stage": stage, "total_jobs": 0}

    rel = {"stage": stage, "total_jobs": total}

    # ── Source breakdown (available at all stages)
    sources = {}
    for j in jobs:
        s = j.get("source", "unknown")
        sources[s] = sources.get(s, 0) + 1
    rel["by_source"] = sources

    # ── Keyword breakdown (available at all stages)
    keywords = {}
    for j in jobs:
        kw = j.get("keyword", "unknown")
        keywords[kw] = keywords.get(kw, 0) + 1
    rel["by_keyword"] = keywords

    # ── Stage-specific metrics

    if stage == "scraped":
        has_desc = sum(1 for j in jobs if len(j.get("description", "")) >= 100)
        rel["with_description"] = has_desc
        rel["without_description"] = total - has_desc

    elif stage == "filtered":
        c_scores = [j.get("composite_score", 0) for j in jobs]
        s_scores = [j.get("semantic_score", 0) for j in jobs]
        rel["composite_score"] = {
            "avg": round(sum(c_scores) / len(c_scores), 3),
            "min": round(min(c_scores), 3),
            "max": round(max(c_scores), 3),
        }
        rel["semantic_score"] = {
            "avg": round(sum(s_scores) / len(s_scores), 3),
            "min": round(min(s_scores), 3),
            "max": round(max(s_scores), 3),
        }
        # Stack breakdown
        stacks = {}
        for j in jobs:
            st = j.get("matched_stack", "unknown")
            stacks[st] = stacks.get(st, 0) + 1
        rel["by_stack"] = stacks
        # Score breakdown averages (5 signals)
        signal_sums = {}
        for j in jobs:
            bd = j.get("score_breakdown", {})
            for k, v in bd.items():
                signal_sums[k] = signal_sums.get(k, 0) + v
        if signal_sums:
            rel["avg_signal_scores"] = {k: round(v / total, 3) for k, v in signal_sums.items()}

    elif stage == "validated":
        c_scores = [j.get("composite_score", 0) for j in jobs if j.get("composite_score")]
        if c_scores:
            rel["composite_score"] = {
                "avg": round(sum(c_scores) / len(c_scores), 3),
                "min": round(min(c_scores), 3),
                "max": round(max(c_scores), 3),
            }
        statuses = {}
        for j in jobs:
            st = j.get("url_status", "unchecked")
            statuses[st] = statuses.get(st, 0) + 1
        rel["by_url_status"] = statuses

    elif stage == "prepared":
        stacks = {}
        for j in jobs:
            st = j.get("matched_stack", "unknown")
            stacks[st] = stacks.get(st, 0) + 1
        rel["by_stack"] = stacks
        has_rag = sum(1 for j in jobs if j.get("resume_context"))
        rel["with_resume_context"] = has_rag
        s_scores = [j.get("semantic_score", 0) for j in jobs if j.get("semantic_score")]
        if s_scores:
            rel["semantic_score"] = {
                "avg": round(sum(s_scores) / len(s_scores), 3),
                "min": round(min(s_scores), 3),
                "max": round(max(s_scores), 3),
            }

    elif stage == "ranked":
        priorities = {}
        for j in jobs:
            p = j.get("priority", "unknown")
            priorities[p] = priorities.get(p, 0) + 1
        rel["by_priority"] = priorities
        dim_sums = {}
        dim_count = 0
        for j in jobs:
            scores = j.get("scores", {})
            if scores:
                dim_count += 1
                for k, v in scores.items():
                    dim_sums[k] = dim_sums.get(k, 0) + v
        if dim_count:
            rel["avg_scores"] = {k: round(v / dim_count, 1) for k, v in dim_sums.items()}
        # Top demanded skills
        skill_counts = {}
        for j in jobs:
            for skill in j.get("matching_skills", []):
                skill_counts[skill] = skill_counts.get(skill, 0) + 1
        if skill_counts:
            top_skills = sorted(skill_counts.items(), key=lambda x: -x[1])[:10]
            rel["top_demanded_skills"] = {k: v for k, v in top_skills}

    return rel
