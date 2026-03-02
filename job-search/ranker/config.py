"""Configuration for the job ranker module."""

import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ─── API Key ─────────────────────────────────────────────────────────────────

ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# ─── Claude Settings ─────────────────────────────────────────────────────────

CLAUDE_MODEL = "claude-sonnet-4-5-20250929"
CLAUDE_MAX_TOKENS = 8192

# ─── Job Analysis Defaults ───────────────────────────────────────────────────

# Fields to keep when slimming scraped jobs for Claude
JOB_FIELDS_FOR_RANKING = [
    "title", "company", "location", "url", "source",
    "date_posted", "keyword", "region",
]
# Max chars of description to send per job for initial ranking
JOB_DESC_TRUNCATE = 600

# Candidate skill keywords for pre-filtering (lowercase)
CANDIDATE_SKILL_KEYWORDS = {
    "devops", "cloud", "platform", "sre", "site reliability", "devsecops",
    "kubernetes", "k8s", "docker", "terraform", "ansible", "helm", "argocd",
    "ci/cd", "cicd", "jenkins", "gitlab", "github actions",
    "azure", "aws", "gcp", "multi-cloud",
    "prometheus", "grafana", "monitoring", "observability",
    "linux", "bash", "python", "infrastructure", "iac",
    "mlops", "ai infrastructure", "llm", "machine learning",
    "security", "vault", "secrets", "kms",
    "nginx", "load balancer", "networking",
}


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
