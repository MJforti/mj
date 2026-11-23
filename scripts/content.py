"""Everything the profile says lives here. Edit this file, then run:

    python scripts/build.py           # re-render every card from this file + data/stats.json
    python scripts/build.py --fetch   # also refresh GitHub stats (needs GITHUB_TOKEN)

The GitHub Action in .github/workflows/profile.yml does the second one every day.
Facts below come from public repositories and the resume in MJforti/linkedin-postyy.
"""

USER = "MJforti"
NAME = "MANTHAN JAIN"

# Degree progress shown on the status card (computed from today's date).
DEGREE = {"label": "B.TECH CSE · CLOUD COMPUTING", "start": "2024-08-01", "end": "2028-08-01"}

HERO = {
    "kicker": "MJFORTI · CLOUD / APPLIED AI / AUTOMATION",
    "statement": ["I turn manual workflows into", "software that ", "runs itself."],
    "lines": [
        "B.Tech CSE, Cloud Computing @ Bennett University, class of 2028.",
        "Building where cloud, applied AI and automation meet.",
    ],
    "command": "deploy ./ideas --to production",
}

# manthan.yaml: (indent, key, value, comment). key=None renders a list item.
ABOUT = [
    (0, "name", "Manthan Jain", None),
    (0, "role", "CSE undergrad, building toward cloud & AI systems engineering", None),
    (0, "studying", "B.Tech CSE (Cloud Computing) @ Bennett University", "2024 - 2028"),
    (0, "builds", "software people use every day: stock, invoices, family finance", None),
    (0, "enjoys", "automating the boring parts, shipping fast, product thinking", None),
    (0, "exploring", "LLM security, AI agents, cloud architecture on AWS", None),
    (0, "next", "scalable cloud-native products, and eventually a company", None),
    (0, "lately", "", None),
    (1, None, "intern @ SKJ Clean Enviro: AI workflows + CI/CD automation", "2026"),
    (1, None, "global alliances @ Weber Innovations", "2025 - 26"),
    (1, None, "creative director @ Mannchala Entertainment", "2024 - now"),
    (0, "proof", "", None),
    (1, None, "AWS Cloud Architecting + AWS Cloud Developing", "certified 2026"),
    (1, None, "1st runner-up, Infuturum 4.0 Hackathon (ACM)", None),
    (1, None, "Smart India Hackathon, shortlisted", None),
]

# Only technologies used in public repos, coursework or certifications.
STACK = [
    ("LANGUAGES", ["typescript", "javascript", "python", "cplusplus", "openjdk:Java", ":SQL"]),
    ("INTERFACE", ["react", "nextdotjs", "tailwindcss", "vite", "pwa:PWA"]),
    ("SERVICES", ["nodedotjs", "express", "fastapi"]),
    ("DATA", ["postgresql", "supabase", "sqlite", "prisma"]),
    ("CLOUD", ["amazonwebservices:AWS", "googlecloud", "vercel", "docker"]),
    ("AI", ["googlegemini:Gemini API", ":Prompt engineering", ":LLM evaluation", ":RAG"]),
    ("TOOLING", ["git", "github", "pytest"]),
]

PROJECTS = [
    {
        "slug": "contextshield",
        "repo": "Prompt-Injection",
        "live": "https://contextshield-iota.vercel.app",
        "kicker": "AI SECURITY · RESEARCH PLATFORM",
        "title": "ContextShield",
        "desc": "Tests how prompt-engineering defenses hold up against indirect prompt "
                "injection: attack compliance, task accuracy and false refusals.",
        "facts": "4 defense strategies · 24 attack cases · team lead",
        "stack": ["nextdotjs", "fastapi", "python", "sqlite"],
        "art": "shield",
    },
    {
        "slug": "invoice-digitizer",
        "repo": "invoice-digitizer",
        "live": None,
        "kicker": "MULTIMODAL AI · OCR PIPELINE",
        "title": "Invoice Digitizer",
        "desc": "Turns multi-page PDF invoices and phone scans into verified Excel sheets with "
                "Gemini vision, model failover and live mobile-to-desktop sync.",
        "facts": "2,000+ invoices for a Tally to SAP migration · 4-week audit in 4 days",
        "stack": ["react", "express", "typescript", "googlegemini:Gemini"],
        "art": "scan",
    },
    {
        "slug": "sampatti",
        "repo": "Sampatti",
        "live": "https://sampatti-one.vercel.app",
        "kicker": "PERSONAL FINANCE · PWA",
        "title": "Sampatti",
        "desc": "A family's payments, EMIs, SIPs, insurance and tax deadlines in one place, "
                "with reminders before every due date.",
        "facts": "row-level security on every write · pg_cron reminder engine",
        "stack": ["nextdotjs", "supabase", "postgresql", "typescript"],
        "art": "dial",
    },
    {
        "slug": "bahubali-stock",
        "repo": "Bahubali-Stock-Management",
        "live": "https://bahubali-stock-management.vercel.app",
        "kicker": "OPERATIONS · OFFLINE-FIRST PWA",
        "title": "Bahubali Stock",
        "desc": "Live stock management for a multi-store hardware business, used by staff "
                "on their phones every day, with or without internet.",
        "facts": "stores + godowns · offline queue that syncs later · PDF / Excel exports",
        "stack": ["react", "vite", "supabase", "tailwindcss"],
        "art": "boxes",
    },
    {
        "slug": "xtag",
        "repo": "xTag-v1-ETHGlobal",
        "live": None,
        "kicker": "AGENTIC AI · HACKATHON BUILD",
        "title": "xTag",
        "desc": "An AI agent that can pay for what it needs: chat intent becomes a paid API "
                "call over the x402 protocol, with on-chain micropayments abstracted away.",
        "facts": "LLM intent parsing · wallet-backed payments · natural-language UI",
        "stack": ["nextdotjs", "googlegemini:Gemini", "prisma", "typescript"],
        "art": "agent",
    },
]

# (state, title, detail): state is done | running | queued
EXPLORING = [
    ("done", "Cloud architecture on AWS", "Cloud Architecting and Cloud Developing certifications"),
    ("running", "LLM security & evaluation", "Measuring prompt-injection defenses with ContextShield"),
    ("running", "Agentic AI", "Agents that reason, call tools and pay for APIs over x402"),
    ("running", "Automation that pays off", "AI workflows and CI/CD pipelines that remove manual work"),
    ("queued", "Kubernetes & Terraform", "Infrastructure as code and orchestration for systems at scale"),
]

SOCIAL = [
    ("github", "GitHub", "https://github.com/MJforti"),
    ("linkedin", "LinkedIn", "https://www.linkedin.com/in/mjf0rti"),
    ("leetcode", "LeetCode", "https://leetcode.com/u/mjforti_/"),
    ("globe", "Portfolio", "https://portfolio-tawny-two-12.vercel.app"),
]

CONNECT = {
    "title": "Let’s build something that runs itself.",
    "sub": "Open to internships, collaborations and ambitious ideas. LinkedIn is the fastest way to reach me.",
}
