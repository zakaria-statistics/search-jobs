#!/usr/bin/env python3
"""
LinkedIn Profile Optimizer — Apify Scraper + Claude API Pipeline
Personalized for Zakaria Elmoumnaoui

Scrapes a LinkedIn profile using Apify's LinkedIn Profile Scraper,
then sends the data to Claude for comprehensive optimization analysis
tailored to DevSecOps/Cloud/Platform Engineer and AI roles in:

EU/UK/Switzerland/Norway/Turkey/Ukraine/Serbia/Iceland/Georgia/Moldova/Albania/Morocco/Tunisia/EU/saudi arabia/qatar.

Requirements:
    python3 -m venv venv
    source venv/bin/activate
    pip install apify-client anthropic python-dotenv rich

Setup:
    Create a .env file with:
        APIFY_API_TOKEN=your_apify_token
        ANTHROPIC_API_KEY=your_anthropic_key

Usage:
    # Scrape + analyze your own profile
    python linkedin_optimizer.py --url "https://www.linkedin.com/in/your-profile/"

    # Analyze a competitor's profile (to learn from their structure)
    python linkedin_optimizer.py --url "https://www.linkedin.com/in/competitor/" --mode competitor

    # Re-analyze from saved scrape (no Apify cost)
    python linkedin_optimizer.py --file scraped_profile.json

    # Custom target role override
    python linkedin_optimizer.py --file profile.json --target-role "Platform Engineer"

    # Full output with HTML report
    python linkedin_optimizer.py --url "https://www.linkedin.com/in/your-profile/" --html
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from textwrap import dedent

try:
    from apify_client import ApifyClient
except ImportError:
    print("❌ Missing: pip install apify-client")
    sys.exit(1)

try:
    import anthropic
except ImportError:
    print("❌ Missing: pip install anthropic")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Optional: rich for pretty console output
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


# ─── Configuration ────────────────────────────────────────────────────────────

APIFY_TOKEN = os.getenv("APIFY_API_TOKEN", "")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")
APIFY_ACTOR_ID = "curious_coder/linkedin-profile-scraper"
CLAUDE_MODEL = "claude-sonnet-4-5-20250929"
CLAUDE_MAX_TOKENS = 8192


# ─── Candidate Profile (Zakaria's context) ────────────────────────────────────

CANDIDATE_CONTEXT = """
## Candidate Context (hard-coded — do NOT ask for this again)

- Name: Zakaria Elmoumnaoui
- Current role: Senior Cloud DevOps Engineer at We Are Beebay (client: Marjane Holding)
- Location: Casablanca, Morocco (open to EU/UK/Switzerland/Norway/Turkey/Ukraine/Serbia/Iceland/Georgia/Moldova/Albania/Morocco/Tunisia/EU/saudi arabia/qatar/canada/usa)
- Experience: 5 years (targeting mid-to-senior DevOps / Cloud / Platform Engineer roles)
- Education: Master's in Big Data & Cloud Computing (ENSET Mohammadia, 2022–2024), Bachelor's in Mathematics & Statistics (Faculty of Sciences Semlalia, 2014–2020)
- Previous role: MTS System

### Core Technical Skills
- Cloud: Azure (AKS, Key Vault, Policy, NSG), AWS, multi-cloud architectures, hybrid cloud
- IaC: Terraform (modules, state management, workspaces), Cloud-init, ARM templates
- Containers: Kubernetes (kubeadm, GKE, EKS, on-prem), Docker, containerd, Helm, ArgoCD (GitOps)
- CI/CD: Jenkins, GitLab CI, GitHub Actions
- Monitoring: Prometheus, Grafana, loki
- DevSecOps: KMS, security scanning, secrets management
- Networking: iptables, firewalls, Linux kernal modules, middleware (Nginx, load balancers, gateways)
- Scripting: Bash, Python, PowerShell
- OS: Ubuntu Server, Debian (Proxmox VE)
- Automation: Ansible, Vagrant

### Differentiators (emphasize these)
- Math/Stats background → analytical, metric-driven approach to infrastructure
- Hands-on home lab (Proxmox on Dell Precision 7780) — practices everything he ships
- Full-stack DevSecOps pipeline (not just CI/CD, but security scanning integrated end-to-end)
- AI/ML infrastructure: RAG pipelines, LLM deployment with Ollama, vector DBs (ChromaDB), GPU workloads
- Multi-cloud breadth (Azure + AWS), not locked to one provider
- hybrid cloud experience (on-prem workloads + cloud), not just public cloud also maintained communication between on-prem and cloud processes
- Real client delivery experience (Marjane Holding) — not just personal projects
- Boomi ELT experience (data pipelines, not just infrastructure)

### Certifications Intended to Pursue (not yet listed on profile, but plan to add)
- CKA (Certified Kubernetes Administrator)
- CKS (Certified Kubernetes Security Specialist)
- CKAD (Certified Kubernetes Application Developer)
- Cloud certifications (Azure Solutions Architect, AWS SysOps Admin)
- HashiCorp certifications (Terraform Associate, Vault Associate)
- AI/ML infrastructure certifications (e.g., Ollama Certified Engineer, vector DB certifications)

### Target Roles (priority order)
1. DevOps Engineer (Mid/Senior)
2. Cloud Engineer / Platform Engineer
3. Site Reliability Engineer (SRE)
4. DevSecOps Engineer
5. AI Infrastructure Engineer / MLOps Engineer

### Target Regions
- France (primary)
- EU (Germany, Netherlands, Belgium, Spain)
- UK
- Switzerland
- Morocco (Casablanca)
EU/UK/Switzerland/Norway/Turkey/Ukraine/Serbia/Iceland/Georgia/Moldova/Albania/Morocco/Tunisia/EU/saudi arabia/qatar/canada/usa

### Portfolio Assets
- GitHub repositories with IaC, CI/CD and AI/MLOps projects
- Personal portfolio website (multilingual)
- Lab projects: Database Lab, Compute Lab, Kubernetes Lab, DevSecOps pipeline, DocAI/RAG
- Planned projects: Secure LLM Infrastructure on Azure/AWS, Kubernetes LLM Agent Platform
"""


# ─── System Prompts ───────────────────────────────────────────────────────────

SYSTEM_PROMPT_SELF = f"""You are an elite LinkedIn profile strategist specializing in DevOps, Cloud, Platform Engineering and AI/MLOps hiring markets across Europe, MENA and north america. You understand what recruiters and ATS systems at companies like OVHcloud, Scaleway, GitLab, HashiCorp, Sopra Steria, Atos, Capgemini, and cloud-native startups scan for.

You will receive a scraped LinkedIn profile JSON from Apify. Produce a surgical, data-driven optimization plan — not generic advice, but specific rewrites, keyword insertions, and structural changes tied to this candidate's actual experience and target market.

{CANDIDATE_CONTEXT}

## Analysis Framework

Score each dimension 0–100 and provide specific fixes:

1. HEADLINE (max 220 chars) — keyword density, value prop, target role alignment
2. ABOUT SECTION — hook strength, Math→DevOps→Cloud→Security→AI/MLOps story, quantified achievements, CTA, keywords
3. EXPERIENCE — STAR/CAR format, metrics, client delivery framing, QA/Release Manager as DevOps strength
4. SKILLS — top 3 pins, missing high-demand skills, deprioritize irrelevant ones
5. EDUCATION — Math background as differentiator, Master's prominence
6. FEATURED/PROJECTS — job work, portfolio labs, GitHub repos, home lab evidence
7. KEYWORD GAP — compare against top DevOps/Cloud job postings in France/EU
8. ALGORITHM — SSI score, content strategy, network growth for target regions

## Output Format

Return ONLY valid JSON (no markdown fences, no preamble):

{{
  "profile_score": {{
    "overall": 0, "headline": 0, "about": 0, "experience": 0,
    "skills": 0, "education": 0, "completeness": 0, "keyword_coverage": 0
  }},
  "critical_issues": [
    {{"area": "", "issue": "", "impact": "high|medium|low", "fix": ""}}
  ],
  "headline_options": [
    {{"text": "", "strategy": "", "target_keywords": []}}
  ],
  "about_rewrite": {{
    "full_text": "", "hook_lines": "", "keywords_embedded": [], "word_count": 0
  }},
  "experience_rewrites": [
    {{
      "company": "", "role": "", "original_bullets": [],
      "optimized_bullets": [], "keywords_added": [], "metrics_added": []
    }}
  ],
  "skills_optimization": {{
    "pin_top_3": [], "add": [], "remove_or_deprioritize": [], "reorder_rationale": ""
  }},
  "keyword_gap_analysis": {{
    "present_strong": [], "present_weak": [], "missing_critical": [],
    "recommended_placements": {{"headline": [], "about": [], "experience": [], "skills": []}}
  }},
  "featured_section": {{
    "recommended_items": [{{"type": "", "title": "", "description": "", "why": ""}}]
  }},
  "quick_wins": [
    {{"action": "", "effort": "5min|30min|1hr|half-day", "impact": "high|medium|low", "priority": 1}}
  ],
  "content_strategy": {{
    "post_topics": [], "posting_frequency": "", "engagement_tactics": [], "hashtags": []
  }},
  "competitor_differentiation": ""
}}"""

SYSTEM_PROMPT_COMPETITOR = f"""You are an elite LinkedIn profile strategist. You will receive a scraped LinkedIn profile JSON of a COMPETITOR — someone in a similar role/market as the candidate below. Your job is to reverse-engineer what makes their profile effective (or ineffective) and extract lessons the candidate can apply.

{CANDIDATE_CONTEXT}

Analyze the competitor profile and return ONLY valid JSON:

{{
  "competitor_summary": {{
    "name": "", "role": "", "experience_years": 0, "location": "",
    "strengths": [], "weaknesses": []
  }},
  "lessons_to_steal": [
    {{"what": "", "where_to_apply": "headline|about|experience|skills|featured", "example": ""}}
  ],
  "keywords_they_use_we_dont": [],
  "structural_patterns": {{
    "headline_pattern": "", "about_structure": "", "bullet_format": ""
  }},
  "differentiation_opportunities": [
    {{"area": "", "they_have": "", "we_can_beat_with": ""}}
  ]
}}"""


# ─── Apify Scraper ────────────────────────────────────────────────────────────

def scrape_linkedin_profile(profile_url: str) -> dict:
    """Scrape a LinkedIn profile using Apify."""
    if not APIFY_TOKEN:
        print("❌ APIFY_API_TOKEN not set. Add it to .env")
        sys.exit(1)

    client = ApifyClient(APIFY_TOKEN)
    log(f"🔍 Scraping: {profile_url}")

    run_input = {
        "profileUrls": [profile_url],
        "proxyConfiguration": {"useApifyProxy": True},
    }

    try:
        run = client.actor(APIFY_ACTOR_ID).call(run_input=run_input)
    except Exception as e:
        print(f"❌ Apify error: {e}")
        print("💡 Verify token + credits: https://console.apify.com/account#/integrations")
        sys.exit(1)

    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    if not items:
        print("❌ No data returned. Profile may be private or URL invalid.")
        sys.exit(1)

    profile = items[0]
    log(f"✅ Scraped: {profile.get('fullName', 'Unknown')}")
    return profile


def load_profile_from_file(filepath: str) -> dict:
    """Load previously scraped profile from JSON."""
    with open(filepath, "r") as f:
        return json.load(f)


# ─── Claude Analyzer ──────────────────────────────────────────────────────────

def analyze_with_claude(profile_data: dict, mode: str = "self", target_role: str = None) -> dict:
    """Send profile to Claude for analysis."""
    if not ANTHROPIC_KEY:
        print("❌ ANTHROPIC_API_KEY not set. Add it to .env")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    system = SYSTEM_PROMPT_SELF if mode == "self" else SYSTEM_PROMPT_COMPETITOR
    profile_json = json.dumps(profile_data, indent=2, default=str)

    user_msg = f"""Analyze and optimize the following LinkedIn profile.
All candidate context is in the system prompt — use it fully.

{"Override target role: " + target_role if target_role else ""}

## Scraped LinkedIn Profile Data (from Apify)

{profile_json}

---

Instructions:
1. Score every dimension honestly — don't inflate
2. Every suggestion must be specific to THIS profile
3. Headline options should each target a different search strategy
4. About rewrite should tell the Math → DevOps → Cloud → Security → AI/MLOps story
5. Experience bullets must include metrics (estimate reasonable ones if absent)
6. Keyword analysis should reflect real job postings for target roles in EU/UK/Switzerland/Norway/Turkey/Ukraine/Serbia/Iceland/Georgia/Moldova/Albania/Morocco/Tunisia/EU/SA/qatar/canada/usa
7. Quick wins prioritized by impact-to-effort ratio"""

    log(f"🤖 Analyzing with {CLAUDE_MODEL}...")
    start = time.time()

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=CLAUDE_MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )
    except anthropic.APIError as e:
        print(f"❌ Claude API error: {e}")
        sys.exit(1)

    elapsed = time.time() - start
    usage = response.usage
    log(f"✅ Done in {elapsed:.1f}s ({usage.input_tokens} in / {usage.output_tokens} out)")

    raw = response.content[0].text.strip()

    # Clean markdown fences
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
    if raw.endswith("```"):
        raw = raw.rsplit("```", 1)[0]
    raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        log("⚠️  Response wasn't valid JSON — saving raw text")
        return {"raw_response": raw}


# ─── Output: Console ──────────────────────────────────────────────────────────

def log(msg: str):
    if HAS_RICH:
        console.print(msg)
    else:
        print(msg)


def print_summary(analysis: dict, mode: str = "self"):
    """Print human-readable summary."""
    if "raw_response" in analysis:
        print("\n📋 Raw Response:\n")
        print(analysis["raw_response"])
        return

    if mode == "competitor":
        print_competitor_summary(analysis)
        return

    scores = analysis.get("profile_score", {})

    if HAS_RICH:
        # Score table
        table = Table(title="📊 Profile Scores", show_header=True)
        table.add_column("Dimension", style="cyan")
        table.add_column("Score", justify="center")
        table.add_column("Grade", justify="center")

        for key, val in scores.items():
            grade = score_to_grade(val) if isinstance(val, (int, float)) else "?"
            table.add_row(key.replace("_", " ").title(), str(val), grade)

        console.print(table)
    else:
        print("\n" + "=" * 60)
        print("📊  LINKEDIN PROFILE OPTIMIZATION REPORT")
        print("=" * 60)
        for key, val in scores.items():
            print(f"   {key.replace('_', ' ').title():20s}: {val}/100")

    # Critical issues
    issues = analysis.get("critical_issues", [])
    if issues:
        print(f"\n🚨 Critical Issues ({len(issues)}):")
        for i, issue in enumerate(issues, 1):
            impact = issue.get("impact", "").upper()
            print(f"   {i}. [{impact}] {issue.get('area', '')}: {issue.get('issue', '')}")
            print(f"      → {issue.get('fix', '')}")

    # Headlines
    headlines = analysis.get("headline_options", [])
    if headlines:
        print(f"\n✏️  Headline Options:")
        for h in headlines:
            print(f"   → \"{h.get('text', '')}\"")
            print(f"     Strategy: {h.get('strategy', '')}")

    # Quick wins
    wins = analysis.get("quick_wins", [])
    if wins:
        print(f"\n⚡ Quick Wins (by priority):")
        for w in sorted(wins, key=lambda x: x.get("priority", 99)):
            print(f"   {w.get('priority', '?')}. [{w.get('effort', '')} / {w.get('impact', '')} impact] {w.get('action', '')}")

    # Missing keywords
    kw = analysis.get("keyword_gap_analysis", {})
    missing = kw.get("missing_critical", [])
    if missing:
        print(f"\n🔑 Critical Missing Keywords: {', '.join(missing)}")

    # Skills
    skills = analysis.get("skills_optimization", {})
    if skills.get("pin_top_3"):
        print(f"\n📌 Pin These Top 3: {', '.join(skills['pin_top_3'])}")
    if skills.get("add"):
        print(f"   ➕ Add: {', '.join(skills['add'])}")

    print()


def print_competitor_summary(analysis: dict):
    """Print competitor analysis summary."""
    summary = analysis.get("competitor_summary", {})
    print(f"\n🔍 Competitor: {summary.get('name', 'Unknown')} — {summary.get('role', '')}")
    print(f"   Strengths: {', '.join(summary.get('strengths', []))}")
    print(f"   Weaknesses: {', '.join(summary.get('weaknesses', []))}")

    lessons = analysis.get("lessons_to_steal", [])
    if lessons:
        print(f"\n🧠 Lessons to Steal:")
        for l in lessons:
            print(f"   • [{l.get('where_to_apply', '')}] {l.get('what', '')}")

    kw = analysis.get("keywords_they_use_we_dont", [])
    if kw:
        print(f"\n🔑 Keywords They Use That We Don't: {', '.join(kw)}")


def score_to_grade(score: int) -> str:
    if score >= 90: return "🟢 A+"
    if score >= 80: return "🟢 A"
    if score >= 70: return "🟡 B"
    if score >= 60: return "🟡 C"
    if score >= 50: return "🟠 D"
    return "🔴 F"


# ─── Output: Markdown Report ──────────────────────────────────────────────────

def generate_markdown_report(analysis: dict, profile_data: dict, output_path: str):
    """Generate a structured Markdown report (git-friendly, renders on GitHub)."""
    scores = analysis.get("profile_score", {})
    issues = analysis.get("critical_issues", [])
    headlines = analysis.get("headline_options", [])
    about = analysis.get("about_rewrite", {})
    exp_rewrites = analysis.get("experience_rewrites", [])
    skills = analysis.get("skills_optimization", {})
    kw = analysis.get("keyword_gap_analysis", {})
    featured = analysis.get("featured_section", {})
    wins = analysis.get("quick_wins", [])
    content = analysis.get("content_strategy", {})
    diff = analysis.get("competitor_differentiation", "")

    lines = []
    w = lines.append  # shorthand

    w(f"# LinkedIn Profile Optimization Report")
    w(f"")
    w(f"> **Candidate:** Zakaria Elmoumnaoui")
    w(f"> **Generated:** {datetime.now().strftime('%B %d, %Y at %H:%M')}")
    w(f"> **Model:** {CLAUDE_MODEL}")
    w(f"")

    # ── Scores ──
    w(f"## Profile Scores")
    w(f"")
    w(f"| Dimension | Score | Grade |")
    w(f"|-----------|:-----:|:-----:|")
    for key, val in scores.items():
        grade = score_to_grade(val) if isinstance(val, (int, float)) else "?"
        w(f"| {key.replace('_', ' ').title()} | {val}/100 | {grade} |")
    w(f"")

    # ── Critical Issues ──
    if issues:
        w(f"## Critical Issues")
        w(f"")
        w(f"| Impact | Area | Issue | Fix |")
        w(f"|:------:|------|-------|-----|")
        for i in issues:
            impact = i.get("impact", "low").upper()
            w(f"| **{impact}** | {i.get('area', '')} | {i.get('issue', '')} | {i.get('fix', '')} |")
        w(f"")

    # ── Headlines ──
    if headlines:
        w(f"## Headline Options")
        w(f"")
        for idx, h in enumerate(headlines, 1):
            w(f"### Option {idx}")
            w(f"")
            w(f"```")
            w(f"{h.get('text', '')}")
            w(f"```")
            w(f"")
            w(f"**Strategy:** {h.get('strategy', '')}")
            w(f"")
            w(f"**Target keywords:** {', '.join(h.get('target_keywords', []))}")
            w(f"")

    # ── About Rewrite ──
    if about:
        w(f"## Optimized About Section")
        w(f"")
        hook = about.get("hook_lines", "")
        if hook:
            w(f"**Hook (first 3 lines — visible before \"See More\"):**")
            w(f"")
            w(f"> {hook}")
            w(f"")
        full = about.get("full_text", "")
        if full:
            w(f"**Full text:**")
            w(f"")
            w(f"```")
            w(f"{full}")
            w(f"```")
            w(f"")
        embedded = about.get("keywords_embedded", [])
        if embedded:
            w(f"**Keywords embedded:** {', '.join(embedded)}")
            w(f"")

    # ── Experience Rewrites ──
    if exp_rewrites:
        w(f"## Experience Rewrites")
        w(f"")
        for exp in exp_rewrites:
            w(f"### {exp.get('role', '')} @ {exp.get('company', '')}")
            w(f"")
            orig = exp.get("original_bullets", [])
            if orig:
                w(f"**Before:**")
                for b in orig:
                    w(f"- {b}")
                w(f"")
            opt = exp.get("optimized_bullets", [])
            if opt:
                w(f"**After (optimized):**")
                for b in opt:
                    w(f"- {b}")
                w(f"")
            kw_added = exp.get("keywords_added", [])
            metrics = exp.get("metrics_added", [])
            if kw_added:
                w(f"**Keywords added:** {', '.join(kw_added)}")
            if metrics:
                w(f"**Metrics added:** {', '.join(metrics)}")
            w(f"")

    # ── Skills ──
    if skills:
        w(f"## Skills Optimization")
        w(f"")
        if skills.get("pin_top_3"):
            w(f"**Pin top 3:** {', '.join(skills['pin_top_3'])}")
        if skills.get("add"):
            w(f"**Add:** {', '.join(skills['add'])}")
        if skills.get("remove_or_deprioritize"):
            w(f"**Remove/deprioritize:** {', '.join(skills['remove_or_deprioritize'])}")
        if skills.get("reorder_rationale"):
            w(f"**Rationale:** {skills['reorder_rationale']}")
        w(f"")

    # ── Keyword Gap ──
    if kw:
        w(f"## Keyword Gap Analysis")
        w(f"")
        if kw.get("present_strong"):
            w(f"**Strong:** `{'` `'.join(kw['present_strong'])}`")
        if kw.get("present_weak"):
            w(f"**Weak (needs reinforcement):** `{'` `'.join(kw['present_weak'])}`")
        if kw.get("missing_critical"):
            w(f"**Missing critical:** `{'` `'.join(kw['missing_critical'])}`")
        w(f"")
        placements = kw.get("recommended_placements", {})
        if placements:
            w(f"**Where to place missing keywords:**")
            w(f"")
            w(f"| Section | Keywords |")
            w(f"|---------|----------|")
            for section, keywords in placements.items():
                if keywords:
                    w(f"| {section.title()} | {', '.join(keywords)} |")
            w(f"")

    # ── Featured Section ──
    items = featured.get("recommended_items", [])
    if items:
        w(f"## Featured Section Recommendations")
        w(f"")
        for item in items:
            w(f"- **[{item.get('type', '')}]** {item.get('title', '')} — {item.get('description', '')}")
            w(f"  - *Why:* {item.get('why', '')}")
        w(f"")

    # ── Quick Wins ──
    if wins:
        w(f"## Quick Wins")
        w(f"")
        w(f"| # | Action | Effort | Impact |")
        w(f"|:-:|--------|:------:|:------:|")
        for win in sorted(wins, key=lambda x: x.get("priority", 99)):
            w(f"| {win.get('priority', '')} | {win.get('action', '')} | {win.get('effort', '')} | {win.get('impact', '')} |")
        w(f"")

    # ── Content Strategy ──
    if content:
        w(f"## Content Strategy")
        w(f"")
        if content.get("posting_frequency"):
            w(f"**Frequency:** {content['posting_frequency']}")
        if content.get("post_topics"):
            w(f"**Topics:** {', '.join(content['post_topics'])}")
        if content.get("hashtags"):
            w(f"**Hashtags:** {' '.join(content['hashtags'])}")
        if content.get("engagement_tactics"):
            w(f"**Tactics:** {', '.join(content['engagement_tactics'])}")
        w(f"")

    # ── Differentiation ──
    if diff:
        w(f"## Competitor Differentiation")
        w(f"")
        w(f"{diff}")
        w(f"")

    # ── Footer ──
    w(f"---")
    w(f"")
    w(f"*Generated by LinkedIn Optimizer — Apify + Claude API pipeline*")

    md = "\n".join(lines)
    with open(output_path, "w") as f:
        f.write(md)
    log(f"📄 Markdown report: {output_path}")


# ─── Save JSON Report ─────────────────────────────────────────────────────────

def save_json_report(analysis: dict, profile_data: dict, output_path: str):
    """Save full report as JSON."""
    report = {
        "generated_at": datetime.now().isoformat(),
        "candidate": "Zakaria Elmoumnaoui",
        "model": CLAUDE_MODEL,
        "profile_data": profile_data,
        "optimization_analysis": analysis,
    }
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    log(f"💾 JSON report: {output_path}")


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    global CLAUDE_MODEL
    parser = argparse.ArgumentParser(
        description="LinkedIn Profile Optimizer — Apify + Claude (Personalized for Zakaria)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=dedent("""\
        Examples:
          %(prog)s --url "https://www.linkedin.com/in/your-profile/"
          %(prog)s --url "https://www.linkedin.com/in/competitor/" --mode competitor
          %(prog)s --file scraped.json --md
          %(prog)s --file scraped.json --target-role "Platform Engineer"
        """),
    )

    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--url", help="LinkedIn profile URL to scrape")
    source.add_argument("--file", help="Path to previously scraped profile JSON")

    parser.add_argument("--mode", choices=["self", "competitor"], default="self",
                        help="'self' = optimize your profile, 'competitor' = learn from theirs")
    parser.add_argument("--target-role", help="Override target role (default: from candidate context)")
    parser.add_argument("--output", "-o", default="linkedin_report.json", help="JSON output path")
    parser.add_argument("--md", action="store_true", help="Also generate Markdown report (.md)")
    parser.add_argument("--save-profile", help="Save raw scraped data to this path")
    parser.add_argument("--model", default=CLAUDE_MODEL, help=f"Claude model (default: {CLAUDE_MODEL})")

    args = parser.parse_args()

    CLAUDE_MODEL = args.model

    log("🚀 LinkedIn Profile Optimizer (Zakaria Edition)")
    log("─" * 50)

    # Step 1: Get profile data
    if args.url:
        profile_data = scrape_linkedin_profile(args.url)
        if args.save_profile:
            with open(args.save_profile, "w") as f:
                json.dump(profile_data, f, indent=2, default=str)
            log(f"💾 Raw profile saved: {args.save_profile}")
    else:
        log(f"📂 Loading from: {args.file}")
        profile_data = load_profile_from_file(args.file)

    # Step 2: Analyze with Claude
    analysis = analyze_with_claude(
        profile_data=profile_data,
        mode=args.mode,
        target_role=args.target_role,
    )

    # Step 3: Output
    print_summary(analysis, mode=args.mode)
    save_json_report(analysis, profile_data, args.output)

    if args.md:
        md_path = args.output.replace(".json", ".md")
        generate_markdown_report(analysis, profile_data, md_path)

    log("\n✨ Done! Review the report and start optimizing.")


if __name__ == "__main__":
    main()
