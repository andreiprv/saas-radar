---
name: saasradar
description: Discover micro-SaaS ideas from Reddit + X threads with subreddit growth analysis.
argument-hint: "[topic]" or "micro SaaS ideas"
context: fork
agent: Explore
disable-model-invocation: true
allowed-tools: Bash, Read, Write, AskUserQuestion
---

# SaaS Radar: Discover Micro-SaaS Ideas from Reddit + X

Discover SaaS opportunities by analyzing what people are asking for, building, and complaining about across Reddit and X over the past 180 days. Prioritizes subreddits showing exponential growth.

## Setup Check

The skill requires at least one API key:

1. **Full Mode** (both keys): Reddit + X - best results with cross-platform signal triangulation
2. **Partial Mode** (one key): Reddit-only or X-only
3. **No keys**: Skill cannot run (API keys required for search tools)

### First-Time Setup

If the user needs to add API keys:

```bash
mkdir -p ~/.config/saas-radar
cat > ~/.config/saas-radar/.env << 'ENVEOF'
# saas-radar API Configuration
# At least one key is required

# For Reddit research (uses OpenAI's web_search tool)
OPENAI_API_KEY=

# For X/Twitter research (uses xAI's x_search tool)
XAI_API_KEY=
ENVEOF

chmod 600 ~/.config/saas-radar/.env
echo "Config created at ~/.config/saas-radar/.env"
echo "Edit to add your API keys."
```

---

## Research Execution

**Step 1: Run the research script**
```bash
python3 ~/.claude/skills/saas-radar/scripts/saas_radar.py "$ARGUMENTS" --emit=compact 2>&1
```

The script will automatically:
- Scan 10 SaaS-relevant subreddits for growth signals (~20s)
- Search Reddit and/or X for SaaS idea signals
- Enrich Reddit threads with real engagement metrics
- Cluster similar ideas to identify market signals
- Score ideas using a 5-factor formula (idea quality, engagement, market signal, growth, recency)
- Output a compact report

**Depth options** (passed through from user's command):
- `--quick` → Faster, fewer sources
- (default) → Balanced
- `--deep` → Comprehensive

---

## Synthesis: Present the Findings

After the script completes, synthesize the output into a structured presentation.

### FIRST: Internalize the Research

Read the compact output carefully. It contains:
1. **Growing Subreddits** - ranked by post acceleration
2. **Top SaaS Ideas** - scored and classified by signal type

Pay attention to:
- **Signal types**: WISH (strongest - people want something that doesn't exist), PROBLEM (pain points), FEATURE_GAP (existing tools missing features), BUILDING (someone already building), WORKFLOW (manual process to automate)
- **Market signals**: Cluster scores indicate multiple independent threads about the same idea (stronger validation)
- **Growth rates**: Ideas from fast-growing subreddits have more momentum
- **Comment insights**: Real quotes from people experiencing the problem

### THEN: Present Results

IMPORTANT: Do NOT wrap output in triple-backtick code blocks. Use markdown tables, bold, blockquotes, and bullet lists — Claude Code renders these properly.

**Display in this sequence:**

**1. Growing Communities** — markdown table:

| # | Subreddit | Growth | Subscribers | Active |
|---|-----------|--------|-------------|--------|
| 1 | r/microsaas | 3.1x | 12.4K | 340 |
| 2 | r/automation | 2.8x | 89K | 1.2K |

**2. Top Ideas by Category** — one table per signal type, starting with the strongest:

**WISHES** (People want something that doesn't exist)

| Score | Idea | Source | Evidence |
|------:|------|--------|----------|
| 80 | Cohort churn analytics for small SaaS | r/microsaas | 717pts, 223cmt, 3.1x growth |
| 72 | Competitor pricing monitor | r/indiehackers | 2 clusters, 1.8x growth |

Then below each table, show detail cards for the top 2-3 ideas as blockquotes:

> **"Quote from thread title"**
> **Audience:** SaaS founders with 100-1K customers
> **Key insight:** "I built a spreadsheet for this but it breaks every month"
> [Source link](url)

**PROBLEMS** (Pain points people are expressing) — same table + blockquote format

**FEATURE GAPS, BUILDING, WORKFLOWS** — same format, only if present

**3. Market Patterns** — bullet list (no code block):

- What themes appear across multiple threads?
- Which subreddits are generating the most ideas?
- Any gaps between what people want and what's being built?

**4. Stats** — bullet list:

**Research complete!**
- **Growth scan:** {n} subreddits analyzed
- **Reddit:** {n} threads, {sum} upvotes, {sum} comments
- **X:** {n} posts, {sum} likes, {sum} reposts
- **Ideas found:** {n}, **Clusters:** {n} market signals
- **Top signals from:** r/{sub1}, r/{sub2}, @{handle1}, @{handle2}

**5. Offer to deep-dive** — plain markdown:

Want me to:
- Deep-dive into a specific idea? (I'll analyze the market, competition, and feasibility)
- Generate a validation plan for any of these ideas?
- Search for more ideas in a specific niche?

---

## Expert Mode

After presenting results, stay in expert mode for follow-up:
- **Deep-dive requests**: Analyze a specific idea's market, competition, and feasibility
- **Validation plans**: Create a step-by-step plan to validate an idea
- **Niche exploration**: Run targeted searches in specific subreddits or topics
- **Answer from research**: Use the data you already have, don't re-run searches

Only re-run the script if the user asks about a completely different topic.

---

## Context Memory

For the rest of this conversation, remember:
- **TOPIC**: {topic}
- **TOP IDEAS**: {list the top 3-5 ideas with scores}
- **GROWING SUBREDDITS**: {which communities are accelerating}
- **KEY PATTERNS**: {cross-cutting themes from the research}
