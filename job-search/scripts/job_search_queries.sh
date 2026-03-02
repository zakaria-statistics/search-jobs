#!/usr/bin/env bash
# job_search_queries.sh — Open job search URLs in browser or print them
# Usage: ./job_search_queries.sh [--open]  (--open to launch in browser)

set -euo pipefail

OPEN_BROWSER=false
[[ "${1:-}" == "--open" ]] && OPEN_BROWSER=true

# Detect OS for browser open command
open_url() {
    if $OPEN_BROWSER; then
        if command -v xdg-open &>/dev/null; then
            xdg-open "$1" 2>/dev/null &
        elif command -v open &>/dev/null; then
            open "$1"
        else
            echo "  → Cannot open browser. URL: $1"
        fi
        sleep 1
    else
        echo "  $1"
    fi
}

TOTAL=0
count_section() { TOTAL=$((TOTAL + $1)); }

echo "============================================"
echo "  JOB SEARCH QUERIES — $(date +%Y-%m-%d)"
echo "============================================"
echo ""

# --- LinkedIn ---
echo "▸ LinkedIn Jobs"
LINKEDIN_QUERIES=(
    "https://www.linkedin.com/jobs/search/?keywords=devops+engineer&location=France&f_E=3%2C4"
    "https://www.linkedin.com/jobs/search/?keywords=cloud+engineer+kubernetes&location=France&f_E=3%2C4"
    "https://www.linkedin.com/jobs/search/?keywords=devsecops&location=European+Union&f_E=3%2C4"
    "https://www.linkedin.com/jobs/search/?keywords=platform+engineer&location=Netherlands&f_E=3%2C4"
    "https://www.linkedin.com/jobs/search/?keywords=SRE+site+reliability&location=France&f_E=3%2C4"
    "https://www.linkedin.com/jobs/search/?keywords=mlops+engineer&location=France&f_E=3%2C4"
    "https://www.linkedin.com/jobs/search/?keywords=devops+engineer&location=Morocco&f_E=3%2C4"
    "https://www.linkedin.com/jobs/search/?keywords=devops+engineer&location=Germany&f_E=3%2C4"
    "https://www.linkedin.com/jobs/search/?keywords=devops+engineer&location=Belgium&f_E=3%2C4"
    "https://www.linkedin.com/jobs/search/?keywords=devops+engineer&location=Switzerland&f_E=3%2C4"
    "https://www.linkedin.com/jobs/search/?keywords=devops+engineer&location=United+Kingdom&f_E=3%2C4"
    "https://www.linkedin.com/jobs/search/?keywords=cloud+engineer&location=Canada&f_E=3%2C4"
    "https://www.linkedin.com/jobs/search/?keywords=devops+engineer&location=Saudi+Arabia&f_E=3%2C4"
)
for url in "${LINKEDIN_QUERIES[@]}"; do open_url "$url"; done
count_section ${#LINKEDIN_QUERIES[@]}
echo ""

# --- Welcome to the Jungle ---
echo "▸ Welcome to the Jungle"
WTTJ_QUERIES=(
    "https://www.welcometothejungle.com/fr/jobs?query=devops&refinementList%5Bcontract_type%5D%5B0%5D=CDI&refinementList%5Bcontract_type%5D%5B1%5D=freelance"
    "https://www.welcometothejungle.com/fr/jobs?query=cloud+engineer"
    "https://www.welcometothejungle.com/fr/jobs?query=devsecops"
    "https://www.welcometothejungle.com/fr/jobs?query=platform+engineer"
    "https://www.welcometothejungle.com/fr/jobs?query=SRE"
    "https://www.welcometothejungle.com/fr/jobs?query=mlops"
)
for url in "${WTTJ_QUERIES[@]}"; do open_url "$url"; done
count_section ${#WTTJ_QUERIES[@]}
echo ""

# --- Indeed France ---
echo "▸ Indeed France"
INDEED_QUERIES=(
    "https://www.indeed.fr/jobs?q=devops+engineer+AWS+Azure&l=Paris"
    "https://www.indeed.fr/jobs?q=ing%C3%A9nieur+devops+kubernetes&l=%C3%8Ele-de-France"
    "https://www.indeed.fr/jobs?q=cloud+engineer+terraform&l=France"
    "https://www.indeed.fr/jobs?q=devsecops&l=France"
)
for url in "${INDEED_QUERIES[@]}"; do open_url "$url"; done
count_section ${#INDEED_QUERIES[@]}
echo ""

# --- APEC ---
echo "▸ APEC"
APEC_QUERIES=(
    "https://www.apec.fr/candidat/recherche-emploi.html/emploi?motsCles=devops&experience=3"
    "https://www.apec.fr/candidat/recherche-emploi.html/emploi?motsCles=cloud+engineer&experience=3"
    "https://www.apec.fr/candidat/recherche-emploi.html/emploi?motsCles=devsecops&experience=3"
)
for url in "${APEC_QUERIES[@]}"; do open_url "$url"; done
count_section ${#APEC_QUERIES[@]}
echo ""

# --- Free-Work ---
echo "▸ Free-Work"
FREEWORK_QUERIES=(
    "https://www.free-work.com/fr/tech-it/jobs?query=devops"
    "https://www.free-work.com/fr/tech-it/jobs?query=cloud+engineer"
    "https://www.free-work.com/fr/tech-it/jobs?query=devsecops"
    "https://www.free-work.com/fr/tech-it/jobs?query=SRE"
)
for url in "${FREEWORK_QUERIES[@]}"; do open_url "$url"; done
count_section ${#FREEWORK_QUERIES[@]}
echo ""

# --- France Tech ---
echo "▸ France Tech Boards"
FRANCE_TECH=(
    "https://welovedevs.com/app/jobs?query=devops"
    "https://www.lesjeudis.com/recherche?q=devops"
    "https://www.chooseyourboss.com/offres/devops"
)
for url in "${FRANCE_TECH[@]}"; do open_url "$url"; done
count_section ${#FRANCE_TECH[@]}
echo ""

# --- Germany ---
echo "▸ Germany"
GERMANY_QUERIES=(
    "https://www.stepstone.de/jobs/devops-engineer"
    "https://www.stepstone.de/jobs/cloud-engineer"
    "https://germantechjobs.de/jobs/DevOps"
    "https://www.arbeitnow.com/?search=devops"
    "https://berlinstartupjobs.com/engineering/?q=devops"
)
for url in "${GERMANY_QUERIES[@]}"; do open_url "$url"; done
count_section ${#GERMANY_QUERIES[@]}
echo ""

# --- Netherlands ---
echo "▸ Netherlands"
NL_QUERIES=(
    "https://www.iamexpat.nl/career/jobs-netherlands?search=devops"
    "https://eurotechjobs.com/jobs?q=devops&l=Netherlands"
    "https://www.nationalevacaturebank.nl/vacature/zoeken?query=devops"
)
for url in "${NL_QUERIES[@]}"; do open_url "$url"; done
count_section ${#NL_QUERIES[@]}
echo ""

# --- Belgium / Luxembourg ---
echo "▸ Belgium / Luxembourg"
BELUX_QUERIES=(
    "https://www.ictjob.be/en/search-it-jobs?keywords=devops"
    "https://www.moovijob.com/search?q=devops"
)
for url in "${BELUX_QUERIES[@]}"; do open_url "$url"; done
count_section ${#BELUX_QUERIES[@]}
echo ""

# --- Switzerland ---
echo "▸ Switzerland"
CH_QUERIES=(
    "https://swissdevjobs.ch/jobs/DevOps"
    "https://www.jobs.ch/en/vacancies/?term=devops"
)
for url in "${CH_QUERIES[@]}"; do open_url "$url"; done
count_section ${#CH_QUERIES[@]}
echo ""

# --- UK ---
echo "▸ United Kingdom"
UK_QUERIES=(
    "https://www.cwjobs.co.uk/jobs/devops"
    "https://www.technojobs.co.uk/devops-jobs"
    "https://www.reed.co.uk/jobs/devops"
)
for url in "${UK_QUERIES[@]}"; do open_url "$url"; done
count_section ${#UK_QUERIES[@]}
echo ""

# --- Morocco / MENA ---
echo "▸ Morocco / MENA"
MOROCCO_QUERIES=(
    "https://www.emploi.ma/recherche-jobs-maroc/devops"
    "https://www.indeed.com/jobs?q=devops&l=Casablanca%2C+Morocco"
    "https://www.bayt.com/en/jobs/?search=devops"
)
for url in "${MOROCCO_QUERIES[@]}"; do open_url "$url"; done
count_section ${#MOROCCO_QUERIES[@]}
echo ""

# --- Gulf ---
echo "▸ Gulf (Saudi Arabia / Qatar / UAE)"
GULF_QUERIES=(
    "https://www.gulftalent.com/jobs/devops"
    "https://www.naukrigulf.com/devops-jobs"
    "https://zerotaxjobs.com/?q=devops"
)
for url in "${GULF_QUERIES[@]}"; do open_url "$url"; done
count_section ${#GULF_QUERIES[@]}
echo ""

# --- Canada ---
echo "▸ Canada"
CA_QUERIES=(
    "https://www.jobbank.gc.ca/jobsearch/jobsearch?searchstring=devops"
    "https://www.jobillico.com/search-jobs?q=devops"
)
for url in "${CA_QUERIES[@]}"; do open_url "$url"; done
count_section ${#CA_QUERIES[@]}
echo ""

# --- Remote ---
echo "▸ Remote-First Boards"
REMOTE_QUERIES=(
    "https://remotive.com/remote-jobs/devops"
    "https://weworkremotely.com/remote-jobs/search?term=devops"
    "https://4dayweek.io/remote-jobs/devops-engineer"
)
for url in "${REMOTE_QUERIES[@]}"; do open_url "$url"; done
count_section ${#REMOTE_QUERIES[@]}
echo ""

# --- DevOps Niche ---
echo "▸ DevOps / Cloud Niche Boards"
NICHE_QUERIES=(
    "https://jobs.cncf.io/?q=devops"
    "https://wellfound.com/role/r/devops-engineer"
)
for url in "${NICHE_QUERIES[@]}"; do open_url "$url"; done
count_section ${#NICHE_QUERIES[@]}
echo ""

# --- Government / Public ---
echo "▸ Government / Public Sector"
GOV_QUERIES=(
    "https://beta.gouv.fr/nous-rejoindre"
    "https://place-emploi-public.gouv.fr/offre-emploi/recherche?motsCles=devops"
    "https://eu-careers.europa.eu/en/job-opportunities"
)
for url in "${GOV_QUERIES[@]}"; do open_url "$url"; done
count_section ${#GOV_QUERIES[@]}
echo ""

# --- Company Career Pages ---
echo "▸ Company Career Pages (rotate 3/week)"
COMPANY_URLS=(
    "https://www.capgemini.com/careers/"
    "https://www.axa.com/en/careers"
    "https://careers.societegenerale.com"
    "https://group.bnpparibas/emploi-carriere"
    "https://orange.jobs"
    "https://recrute.carrefour.fr"
    "https://www.soprasteria.com/careers"
    "https://atos.net/en/careers"
    "https://www.thalesgroup.com/en/careers"
    "https://www.cgi.com/en/careers"
    "https://careers.datadoghq.com"
    "https://about.gitlab.com/jobs"
    "https://grafana.com/careers"
    "https://canonical.com/careers"
    "https://ing.jobs"
)
for url in "${COMPANY_URLS[@]}"; do open_url "$url"; done
count_section ${#COMPANY_URLS[@]}
echo ""

echo "============================================"
echo "  Done. Total search queries: $TOTAL"
echo "  Run with --open to launch all in browser"
echo "============================================"
