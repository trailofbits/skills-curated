# last30days

Research any topic from the last 30 days across Reddit, X, and the web. Surfaces real community discussions with engagement metrics (upvotes, likes, reposts) and synthesizes findings into actionable insights.

## Install

```
/plugin install trailofbits/skills-curated/plugins/last30days
```

## Prerequisites

- **OpenAI API key** -- powers Reddit search via OpenAI's `web_search` tool
- **xAI API key** -- powers X/Twitter search via xAI's `x_search` tool

Both keys are optional. The skill degrades gracefully: with no keys, it falls back to web search only. With one key, it searches that source plus web.

## Setup

Create a config file at `~/.config/last30days/.env`:

```bash
mkdir -p ~/.config/last30days
cat > ~/.config/last30days/.env << 'EOF'
OPENAI_API_KEY=sk-...
XAI_API_KEY=xai-...
EOF
```

Environment variables (`OPENAI_API_KEY`, `XAI_API_KEY`) override the config file if set.

## Usage

```
/last30days Claude Code skills
/last30days best AI video tools --deep
/last30days NVIDIA news --days=7
/last30days nano banana pro prompts for Gemini --quick
```

### Options

| Flag | Effect |
|------|--------|
| `--days=N` | Look back N days instead of 30 (1-30) |
| `--quick` | Fewer sources, faster results (8-12 each) |
| `--deep` | More sources, comprehensive research (50-70 Reddit, 40-60 X) |
| `--include-web` | Add web search alongside Reddit/X |

## Credits

Based on [mvanhorn/last30days-skill](https://github.com/mvanhorn/last30days-skill), licensed under MIT.
