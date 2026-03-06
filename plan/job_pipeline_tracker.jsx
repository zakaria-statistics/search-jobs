import { useState, useEffect, useRef } from "react";

const PHASES = [
  {
    id: 1,
    title: "Foundation",
    subtitle: "Basic Scraping",
    status: "complete",
    color: "#10b981",
    icon: "⛏",
    dateRange: "Mar 1–2",
    commits: "120b7af → a7d4130",
    items: [
      { what: "Multi-source scraping", detail: "Indeed, RemoteOK, Arbeitnow, Rekrute, WTTJ", done: true },
      { what: "Keyword matching", detail: "5-tier: title phrase → title word → tag phrase → tag strict → description lenient", done: true },
      { what: "Output", detail: "Timestamped JSON (scraped_YYYY-MM-DD-HH-MM-SS.json) with deduplication", done: true },
      { what: "Indeed multi-region", detail: "9 country domains (MA, FR, DE, NL, BE, LU, PL, CH, UK)", done: true },
    ],
  },
  {
    id: 2,
    title: "AI Ranking",
    subtitle: "Claude Integration",
    status: "complete",
    color: "#8b5cf6",
    icon: "🧠",
    dateRange: "Mar 1",
    commits: "d7f1228",
    items: [
      { what: "Claude API scoring", detail: "4 dimensions: skills (40%), experience (30%), location (15%), growth (15%)", done: true },
      { what: "Priority labels", detail: "apply_now, strong_match, worth_trying, long_shot, skip", done: true },
      { what: "Job slimming", detail: "slim_job() strips heavy fields, extract_skill_sentences() for token efficiency", done: true },
      { what: "Keyword pre-filter", detail: "34 skill terms in CANDIDATE_SKILL_KEYWORDS gate Claude calls", done: true },
    ],
  },
  {
    id: 3,
    title: "Semantic Intelligence",
    subtitle: "Vector DB + RAG",
    status: "complete",
    color: "#3b82f6",
    icon: "🔮",
    dateRange: "Mar 5",
    commits: "79092ee",
    items: [
      { what: "ChromaDB vector store", detail: "Persistent at output/.chromadb/, cosine similarity space", done: true },
      { what: "Resume indexing", detail: "8 variants (AI/AWS/Azure/DevOps × EN/FR) chunked by ## headings", done: true },
      { what: "Semantic pre-filter", detail: "Cosine similarity threshold 0.65; runs locally, no API cost", done: true },
      { what: "RAG context", detail: "Matched resume chunks sent to Claude per-job", done: true },
      { what: "Stack-aware matching", detail: "Auto-detects best resume variant (ai/aws/azure/devops) per job", done: true },
      { what: "Change detection", detail: "MD5 hash-based auto-reindexing when resume files change", done: true },
    ],
  },
  {
    id: 4,
    title: "Composite Scoring",
    subtitle: "Multi-Signal Ranking",
    status: "complete",
    color: "#f59e0b",
    icon: "📊",
    dateRange: "Mar 6",
    commits: "705ab8f",
    items: [
      { what: "5-dimension composite score", detail: "Replaces semantic-only sorting", done: true },
      { what: "Weights", detail: "semantic (0.35), skill_match (0.30), title_match (0.20), location (0.10), stack_depth (0.05)", done: true },
      { what: "Score buckets", detail: "top (0.75+), strong (0.60–0.75), moderate (0.45–0.60)", done: true },
      { what: "Score breakdown", detail: "Per-job breakdown showing why it ranked high or low", done: true },
      { what: "False positive reduction", detail: "Semantic-only high scores pushed down if poor title/skill match", done: true },
    ],
  },
  {
    id: 5,
    title: "Pipeline Maturity",
    subtitle: "Tracking & Workflow",
    status: "complete",
    color: "#ef4444",
    icon: "🚀",
    dateRange: "Mar 1–6",
    commits: "a7d4130 → 705ab8f",
    items: [
      { what: "Indeed enrichment", detail: "Full description fetch with extract_skill_sentences() (top 50 jobs)", done: true },
      { what: "Application tracker", detail: "opportunity_tracker.py — status flow, follow-up scheduling, import/export", done: true },
      { what: "Contact pipeline", detail: "contact_pipeline.py — recruiter outreach with auto-cadence (Day 0/3/10)", done: true },
      { what: "Interactive review", detail: "pipeline.py review — approve/skip/view per job, auto-imports to tracker", done: true },
      { what: "Pipeline status", detail: "pipeline.py status — health check across all stages", done: true },
      { what: "Output organization", detail: "Timestamped run directories (scraped_*, filtered_*, ranked_*)", done: true },
    ],
  },
];

const FUTURE = [
  { title: "Auto-application drafting", detail: "Cover letter generation per job", icon: "✉️" },
  { title: "Interview prep generation", detail: "Company-specific question banks", icon: "🎯" },
  { title: "Market trend analytics", detail: "Skill demand & salary ranges over time", icon: "📈" },
  { title: "Resume auto-tailoring", detail: "Adjust emphasis based on matched skills", icon: "🔧" },
];

const STATUS_MAP = {
  complete: { label: "Complete", bg: "#065f46", text: "#6ee7b7" },
  in_progress: { label: "In Progress", bg: "#713f12", text: "#fde047" },
  planned: { label: "Planned", bg: "#1e3a5f", text: "#93c5fd" },
};

function CheckIcon({ done }) {
  if (done) {
    return (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
        <circle cx="9" cy="9" r="9" fill="#10b981" opacity="0.15" />
        <path d="M5.5 9.5L7.5 11.5L12.5 6.5" stroke="#10b981" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <circle cx="9" cy="9" r="9" fill="#475569" opacity="0.2" />
      <circle cx="9" cy="9" r="3" fill="#475569" opacity="0.4" />
    </svg>
  );
}

function PhaseCard({ phase, isExpanded, onToggle, index }) {
  const status = STATUS_MAP[phase.status];
  const doneCount = phase.items.filter((i) => i.done).length;
  const totalCount = phase.items.length;
  const pct = Math.round((doneCount / totalCount) * 100);

  return (
    <div
      style={{
        background: "rgba(15,23,42,0.6)",
        border: `1px solid ${isExpanded ? phase.color + "66" : "rgba(148,163,184,0.1)"}`,
        borderRadius: 16,
        overflow: "hidden",
        transition: "all 0.3s cubic-bezier(0.4,0,0.2,1)",
        backdropFilter: "blur(12px)",
        animation: `fadeSlideIn 0.5s ease ${index * 0.08}s both`,
      }}
    >
      <div
        onClick={onToggle}
        style={{
          padding: "20px 24px",
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          gap: 16,
          userSelect: "none",
        }}
      >
        <div
          style={{
            width: 48,
            height: 48,
            borderRadius: 12,
            background: `linear-gradient(135deg, ${phase.color}22, ${phase.color}11)`,
            border: `1px solid ${phase.color}33`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 22,
            flexShrink: 0,
          }}
        >
          {phase.icon}
        </div>

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            <span style={{ color: phase.color, fontSize: 11, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", fontFamily: "'JetBrains Mono', monospace" }}>
              Phase {phase.id}
            </span>
            <span
              style={{
                fontSize: 10,
                fontWeight: 600,
                padding: "2px 8px",
                borderRadius: 6,
                background: status.bg,
                color: status.text,
                letterSpacing: "0.04em",
                fontFamily: "'JetBrains Mono', monospace",
              }}
            >
              {status.label}
            </span>
          </div>
          <div style={{ color: "#e2e8f0", fontSize: 17, fontWeight: 600, marginTop: 2, fontFamily: "'DM Sans', sans-serif" }}>
            {phase.title}
            <span style={{ color: "#64748b", fontWeight: 400, marginLeft: 8, fontSize: 14 }}>{phase.subtitle}</span>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 16, flexShrink: 0 }}>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: 22, fontWeight: 700, color: "#e2e8f0", fontFamily: "'JetBrains Mono', monospace", lineHeight: 1 }}>
              {pct}%
            </div>
            <div style={{ fontSize: 11, color: "#64748b", fontFamily: "'JetBrains Mono', monospace" }}>
              {doneCount}/{totalCount}
            </div>
          </div>
          <div
            style={{
              width: 60,
              height: 6,
              borderRadius: 3,
              background: "rgba(148,163,184,0.1)",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                height: "100%",
                width: `${pct}%`,
                borderRadius: 3,
                background: `linear-gradient(90deg, ${phase.color}, ${phase.color}cc)`,
                transition: "width 0.6s ease",
              }}
            />
          </div>
          <svg
            width="20"
            height="20"
            viewBox="0 0 20 20"
            fill="none"
            style={{
              transform: isExpanded ? "rotate(180deg)" : "rotate(0deg)",
              transition: "transform 0.3s ease",
              flexShrink: 0,
            }}
          >
            <path d="M5 8L10 13L15 8" stroke="#64748b" strokeWidth="2" strokeLinecap="round" />
          </svg>
        </div>
      </div>

      {isExpanded && (
        <div
          style={{
            borderTop: "1px solid rgba(148,163,184,0.08)",
            padding: "16px 24px 20px",
            animation: "expandIn 0.3s ease",
          }}
        >
          <div style={{ display: "flex", gap: 16, marginBottom: 16, flexWrap: "wrap" }}>
            <span style={{ fontSize: 11, color: "#94a3b8", fontFamily: "'JetBrains Mono', monospace" }}>
              📅 {phase.dateRange}
            </span>
            <span style={{ fontSize: 11, color: "#94a3b8", fontFamily: "'JetBrains Mono', monospace" }}>
              🔗 {phase.commits}
            </span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {phase.items.map((item, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  gap: 12,
                  alignItems: "flex-start",
                  padding: "10px 14px",
                  borderRadius: 10,
                  background: item.done ? "rgba(16,185,129,0.04)" : "rgba(71,85,105,0.06)",
                  border: `1px solid ${item.done ? "rgba(16,185,129,0.08)" : "rgba(71,85,105,0.08)"}`,
                  animation: `fadeSlideIn 0.3s ease ${i * 0.04}s both`,
                }}
              >
                <div style={{ paddingTop: 2, flexShrink: 0 }}>
                  <CheckIcon done={item.done} />
                </div>
                <div>
                  <div style={{ color: "#e2e8f0", fontSize: 14, fontWeight: 600, fontFamily: "'DM Sans', sans-serif" }}>
                    {item.what}
                  </div>
                  <div style={{ color: "#94a3b8", fontSize: 12, marginTop: 2, lineHeight: 1.5, fontFamily: "'JetBrains Mono', monospace" }}>
                    {item.detail}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function JobPipelineTracker() {
  const [expanded, setExpanded] = useState(new Set([4]));
  const [showAll, setShowAll] = useState(false);

  const toggle = (id) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const totalItems = PHASES.reduce((s, p) => s + p.items.length, 0);
  const doneItems = PHASES.reduce((s, p) => s + p.items.filter((i) => i.done).length, 0);
  const overallPct = Math.round((doneItems / totalItems) * 100);

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "linear-gradient(145deg, #0a0f1a 0%, #0f172a 40%, #0c1220 100%)",
        color: "#e2e8f0",
        fontFamily: "'DM Sans', sans-serif",
        padding: "32px 16px",
      }}
    >
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap');
        @keyframes fadeSlideIn {
          from { opacity: 0; transform: translateY(12px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes expandIn {
          from { opacity: 0; max-height: 0; }
          to { opacity: 1; max-height: 2000px; }
        }
        @keyframes pulseGlow {
          0%, 100% { box-shadow: 0 0 20px rgba(59,130,246,0.1); }
          50% { box-shadow: 0 0 30px rgba(59,130,246,0.2); }
        }
        * { box-sizing: border-box; }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(148,163,184,0.2); border-radius: 3px; }
      `}</style>

      <div style={{ maxWidth: 820, margin: "0 auto" }}>
        {/* Header */}
        <div style={{ marginBottom: 36, animation: "fadeSlideIn 0.5s ease" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
            <div
              style={{
                width: 10,
                height: 10,
                borderRadius: "50%",
                background: "#10b981",
                boxShadow: "0 0 8px rgba(16,185,129,0.5)",
              }}
            />
            <span style={{ fontSize: 12, color: "#10b981", fontFamily: "'JetBrains Mono', monospace", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase" }}>
              Active Project
            </span>
          </div>
          <h1 style={{ fontSize: 32, fontWeight: 700, margin: 0, lineHeight: 1.2, letterSpacing: "-0.02em" }}>
            Job Search Pipeline
          </h1>
          <p style={{ color: "#64748b", fontSize: 15, margin: "6px 0 0", fontFamily: "'JetBrains Mono', monospace" }}>
            Scrape → Filter → Rank → Track → Apply
          </p>
        </div>

        {/* Overall Progress */}
        <div
          style={{
            background: "rgba(15,23,42,0.6)",
            border: "1px solid rgba(148,163,184,0.1)",
            borderRadius: 16,
            padding: "20px 24px",
            marginBottom: 28,
            backdropFilter: "blur(12px)",
            animation: "fadeSlideIn 0.5s ease 0.1s both",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <span style={{ fontSize: 13, color: "#94a3b8", fontWeight: 600 }}>Overall Progress</span>
            <span style={{ fontSize: 24, fontWeight: 700, fontFamily: "'JetBrains Mono', monospace", color: "#e2e8f0" }}>
              {overallPct}%
            </span>
          </div>
          <div style={{ height: 8, borderRadius: 4, background: "rgba(148,163,184,0.08)", overflow: "hidden" }}>
            <div
              style={{
                height: "100%",
                width: `${overallPct}%`,
                borderRadius: 4,
                background: "linear-gradient(90deg, #10b981, #3b82f6, #8b5cf6)",
                transition: "width 1s ease",
              }}
            />
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", marginTop: 10 }}>
            <span style={{ fontSize: 12, color: "#64748b", fontFamily: "'JetBrains Mono', monospace" }}>
              {doneItems}/{totalItems} tasks complete
            </span>
            <span style={{ fontSize: 12, color: "#64748b", fontFamily: "'JetBrains Mono', monospace" }}>
              5 phases • Mar 1–6, 2026
            </span>
          </div>
        </div>

        {/* Expand/Collapse */}
        <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 12 }}>
          <button
            onClick={() => {
              if (showAll) {
                setExpanded(new Set());
                setShowAll(false);
              } else {
                setExpanded(new Set(PHASES.map((p) => p.id)));
                setShowAll(true);
              }
            }}
            style={{
              background: "rgba(148,163,184,0.08)",
              border: "1px solid rgba(148,163,184,0.12)",
              borderRadius: 8,
              padding: "6px 14px",
              color: "#94a3b8",
              fontSize: 12,
              cursor: "pointer",
              fontFamily: "'JetBrains Mono', monospace",
              fontWeight: 500,
              transition: "all 0.2s",
            }}
            onMouseEnter={(e) => {
              e.target.style.background = "rgba(148,163,184,0.14)";
              e.target.style.color = "#e2e8f0";
            }}
            onMouseLeave={(e) => {
              e.target.style.background = "rgba(148,163,184,0.08)";
              e.target.style.color = "#94a3b8";
            }}
          >
            {showAll ? "▲ Collapse All" : "▼ Expand All"}
          </button>
        </div>

        {/* Phases */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {PHASES.map((phase, i) => (
            <PhaseCard
              key={phase.id}
              phase={phase}
              isExpanded={expanded.has(phase.id)}
              onToggle={() => toggle(phase.id)}
              index={i}
            />
          ))}
        </div>

        {/* What's Next */}
        <div style={{ marginTop: 36, animation: "fadeSlideIn 0.5s ease 0.5s both" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
            <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#f59e0b", boxShadow: "0 0 8px rgba(245,158,11,0.4)" }} />
            <span style={{ fontSize: 12, color: "#f59e0b", fontFamily: "'JetBrains Mono', monospace", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase" }}>
              What's Next
            </span>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12 }}>
            {FUTURE.map((item, i) => (
              <div
                key={i}
                style={{
                  background: "rgba(15,23,42,0.4)",
                  border: "1px solid rgba(148,163,184,0.08)",
                  borderRadius: 12,
                  padding: "16px 18px",
                  animation: `fadeSlideIn 0.4s ease ${0.6 + i * 0.08}s both`,
                  transition: "border-color 0.2s",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.borderColor = "rgba(245,158,11,0.25)")}
                onMouseLeave={(e) => (e.currentTarget.style.borderColor = "rgba(148,163,184,0.08)")}
              >
                <div style={{ fontSize: 20, marginBottom: 8 }}>{item.icon}</div>
                <div style={{ color: "#e2e8f0", fontSize: 14, fontWeight: 600, marginBottom: 4 }}>{item.title}</div>
                <div style={{ color: "#64748b", fontSize: 12, fontFamily: "'JetBrains Mono', monospace", lineHeight: 1.5 }}>
                  {item.detail}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div style={{ textAlign: "center", marginTop: 40, color: "#334155", fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}>
          zack · job-search-pipeline · last updated Mar 6, 2026
        </div>
      </div>
    </div>
  );
}