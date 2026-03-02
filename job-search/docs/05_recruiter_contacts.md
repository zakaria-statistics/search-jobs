# 05 — Recruiter & Tech Lead Contact Strategy

## Who to Contact (by company type)

### At Target Companies (Direct Hiring)

| Role to find | Why | How to find |
|--------------|-----|-------------|
| **Engineering Manager / Tech Lead** | Decision maker, knows team needs | LinkedIn: `"tech lead" "devops" "société générale"` |
| **Talent Acquisition / IT Recruiter** | Owns the pipeline | LinkedIn: `"talent acquisition" "IT" "BNP Paribas"` |
| **Head of Platform / Cloud** | Knows roadmap, can refer | LinkedIn: `"head of platform" "AXA"` |
| **DevOps Engineers (peers)** | Internal referrals, culture info | LinkedIn: `"devops engineer" "Orange Business"` |

### At ESN / Consulting Firms

| Role to find | Why | How to find |
|--------------|-----|-------------|
| **Business Manager / Ingénieur d'affaires** | Places consultants at clients | LinkedIn: `"ingénieur d'affaires" "Capgemini" "DevOps"` |
| **Delivery Manager** | Manages consultant teams | LinkedIn: `"delivery manager" "Sopra Steria"` |
| **Technical Recruiter** | First contact point | LinkedIn: `"recruteur IT" "Atos"` |

---

## LinkedIn Search Templates

Use these in the LinkedIn search bar (People filter):

```
"talent acquisition" AND "DevOps" AND ("Société Générale" OR "BNP Paribas" OR "AXA")
"tech lead" AND "cloud" AND ("Capgemini" OR "Orange Business")
"engineering manager" AND "platform" AND (France OR Netherlands)
"ingénieur d'affaires" AND "DevOps" AND (Paris OR Lyon)
"recruteur" AND "cloud" AND (Casablanca OR Rabat)
```

---

## Outreach Templates

### Template 1 — Cold outreach to Recruiter (French)

```
Objet: Ingénieur DevOps — AWS/Azure/Kubernetes — Disponible

Bonjour [Prénom],

Je me permets de vous contacter car je suis actuellement à la recherche
d'un poste d'ingénieur DevOps/Cloud (CDI ou freelance).

Mon profil en bref :
• 3-5 ans d'expérience en DevOps/Cloud
• AWS + Azure, Kubernetes, Terraform, CI/CD (GitLab CI, GitHub Actions)
• Bilingue français/anglais

Je serais ravi d'échanger si vous avez des missions ou postes
correspondants chez [Entreprise] ou chez vos clients.

Bien cordialement,
[Nom]
```

### Template 2 — Cold outreach to Tech Lead (English)

```
Subject: DevOps/Cloud Engineer — interested in [Company] opportunities

Hi [Name],

I came across your profile and noticed you lead the [DevOps/Platform/Cloud]
team at [Company]. I'm a mid-level DevOps engineer with experience in
AWS, Azure, Kubernetes, and Terraform — and I'm exploring new opportunities.

Would you be open to a quick chat about what your team is working on
and if there are any open roles?

Thanks,
[Name]
```

### Template 3 — Referral ask to Peer Engineer

```
Salut [Prénom],

J'ai vu que tu travailles en tant que [Role] chez [Entreprise].
Je cherche actuellement un poste similaire — est-ce que tu aurais
des infos sur les recrutements en cours dans ton équipe ?

Si tu es dispo pour un café virtuel de 15 min, ce serait super.

Merci !
[Nom]
```

---

## Follow-Up Cadence

| Day | Action |
|-----|--------|
| Day 0 | Send initial connection request + message |
| Day 3 | If no reply, send follow-up on LinkedIn |
| Day 7 | If connected but no reply, send short reminder |
| Day 14 | Final follow-up: "Just checking if timing works" |
| Day 21+ | Move to "cold — revisit in 30 days" |

**Rules:**
- Never send more than **3 follow-ups** total
- Personalize every message (mention something specific about their team/company)
- Best times to send: **Tuesday–Thursday, 9:00–11:00 AM** local time
- Track all outreach in `scripts/contact_pipeline.py`

---

## Contact Tracking Table

| # | Name | Company | Role | Platform | Message sent | Follow-up 1 | Follow-up 2 | Status | Notes |
|---|------|---------|------|----------|-------------|-------------|-------------|--------|-------|
| 1 | — | — | — | LinkedIn | — | — | — | New | — |

> Statuses: `New` → `Sent` → `Connected` → `Replied` → `Call scheduled` → `Referred` / `No response`

---

## Networking Events & Communities

| Event/Community | Type | URL | Frequency |
|----------------|------|-----|-----------|
| DevOps D-Day | Conference (Marseille) | devopsdday.com | Annual (Nov) |
| Devoxx France | Conference (Paris) | devoxx.fr | Annual (Apr) |
| KubeCon EU | Conference (rotating EU city) | events.linuxfoundation.org | Annual |
| Paris DevOps Meetup | Meetup | meetup.com/paris-devops | Monthly |
| Cloud Native Morocco | Community | LinkedIn group | Ongoing |
| French Tech Slack/Discord | Community | Various | Ongoing |
| AFUP (PHP but good network) | Meetup/Conference | afup.org | Regular |

**Tip:** Attend 1–2 meetups/month. Mention you're looking — word of mouth is the #1 referral channel in France.
