# SaaS Radar

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that discovers micro-SaaS ideas from Reddit and X (Twitter).

It scans 10 SaaS-relevant subreddits for growth signals, searches both platforms for pain points and wishes, then scores and ranks ideas using engagement metrics, market signals, and community growth data.

## Install

**1. Clone the repo**

```bash
git clone https://github.com/youruser/saas-radar.git
cd saas-radar
```

**2. Link it as a Claude Code skill**

On macOS/Linux:
```bash
ln -s "$(pwd)" ~/.claude/skills/saas-radar
```

On Windows (PowerShell as admin):
```powershell
New-Item -ItemType Junction -Path "$env:USERPROFILE\.claude\skills\saas-radar" -Target (Get-Location)
```

**3. Add API keys**

You need at least one key. Both is better.

```bash
mkdir -p ~/.config/saas-radar

cat > ~/.config/saas-radar/.env << 'EOF'
# For Reddit search (uses OpenAI's web_search tool)
OPENAI_API_KEY=sk-...

# For X/Twitter search (uses xAI's x_search tool)
XAI_API_KEY=xai-...
EOF

chmod 600 ~/.config/saas-radar/.env
```

## Usage

In Claude Code, type:

```
/saasradar micro SaaS ideas
```

Or with options:

```
/saasradar developer tools --quick
/saasradar automation for small businesses --deep
```

### Options

| Flag | What it does |
|------|-------------|
| `--quick` | Fewer results, faster |
| `--deep` | More results, slower |
| `--sources=reddit` | Reddit only (skip X) |
| `--sources=x` | X only (skip Reddit) |

### What you get

1. **Growing subreddits** — Which SaaS communities are accelerating
2. **Ranked ideas** — Scored by idea quality, engagement, market signal, growth, and recency
3. **Signal types** — Each idea classified as wish, problem, feature gap, building, or workflow
4. **Comment insights** — Real quotes from people experiencing the problem

### Example output

```
Growing Subreddits:
1. r/microsaas (3.1x acceleration, 12.4K subs, 340 active)
2. r/automation (2.8x acceleration, 89K subs, 1.2K active)

Top SaaS Ideas:

R1 (76) [WISH] r/microsaas | 2026-01-15 | growth:3.1x | 482pts 67cmt
  "Why isn't there a simple tool to track SaaS churn by cohort?"
  Idea: Cohort churn analytics dashboard for small SaaS
  Audience: SaaS founders with 100-1000 customers
  Insights:
    - "I built a spreadsheet for this but it breaks every month"
    - "ChartMogul is too expensive for early-stage"
```

## Test without API keys

Mock mode runs the full pipeline with fixture data:

```bash
python3 scripts/saas_radar.py "micro SaaS ideas" --mock
```

## How it works

1. **Growth scan** — Checks 10 subreddits (r/SaaS, r/microsaas, r/indiehackers, etc.) for posting velocity and engagement trends
2. **Search** — Queries Reddit via OpenAI and X via xAI in parallel, looking for pain points, wishes, and builders
3. **Enrich** — Fetches real upvotes, comments, and top insights from each Reddit thread
4. **Cluster** — Groups similar ideas to detect market signals (multiple people wanting the same thing)
5. **Score** — 5-factor formula: idea quality (30%), engagement (25%), market signal (20%), growth (15%), recency (10%)
6. **Render** — Outputs a compact report that Claude synthesizes into actionable insights

## Requirements

- Python 3.9+
- Claude Code
- At least one API key (OpenAI or xAI)
- No pip dependencies (stdlib only)
