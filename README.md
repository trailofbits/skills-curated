# Curated Skills Marketplace

Trail of Bits' reviewed and approved Claude Code plugins. Every skill and marketplace here has been vetted for quality and safety.

## Why This Exists

We don't want people at Trail of Bits installing random plugins from GitHub repos we haven't reviewed. Published skills have been found with backdoors and malicious hooks, and the ecosystem has no built-in quality gate. This repo is how we solve that problem internally.

Everything here has been code-reviewed by Trail of Bits staff. We're sharing it publicly so the broader community benefits from the same vetting.

## Installation

```
/plugin marketplace add trailofbits/skills-curated
/plugin menu
```

## Available Plugins

### Development

| Plugin | Description |
|--------|-------------|
| [planning-with-files](plugins/planning-with-files/) | File-based planning with persistent markdown for complex multi-step tasks |
| [skill-extractor](plugins/skill-extractor/) | Extract reusable skills from work sessions |

### Security

| Plugin | Description |
|--------|-------------|
| [ffuf-web-fuzzing](plugins/ffuf-web-fuzzing/) | Expert guidance for ffuf web fuzzing during authorized penetration testing |
| [wooyun-legacy](plugins/wooyun-legacy/) | Web vulnerability testing methodology from 88,636 real-world cases (WooYun 2010-2016) |

### Writing

| Plugin | Description |
|--------|-------------|
| [humanizer](plugins/humanizer/) | Identifies and removes AI writing patterns to make text sound natural |

## How It Works

There are three ways to get a skill approved for use:

### 1. Use an approved marketplace

The marketplaces below have been reviewed and are approved for use. Install plugins from them directly.

| Marketplace | Focus |
|-------------|-------|
| [trailofbits/skills](https://github.com/trailofbits/skills) | Trail of Bits original skills for security research and auditing |
| [trailofbits/skills-curated](https://github.com/trailofbits/skills-curated) | Community skills curated and distributed by Trail of Bits |
| [trailofbits/skills-internal](https://github.com/trailofbits/skills-internal) | Trail of Bits internal skills (private) |
| [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official) | Anthropic's official plugins |
| [anthropics/knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins) | Anthropic's official knowledge work plugins |
| [obra/superpowers](https://github.com/obra/superpowers) | Advanced workflow patterns, TDD enforcement, multi-skill orchestration |
| [EveryInc/compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) | Production engineering workflows and multi-agent review |
| [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | Marketing-focused skills |
| [openai/skills](https://github.com/openai/skills) | OpenAI's official skills catalog for Codex |

### 2. Request approval of a new marketplace

Found a marketplace not on the list? [Open an issue](https://github.com/trailofbits/skills-curated/issues/new) requesting approval. Include the repo URL and what you're using it for. We'll review it and add it to the approved list if it passes.

### 3. Submit an individual skill

Using a skill from an unapproved source? Open a PR to add it here. See [CLAUDE.md](CLAUDE.md) for authoring guidelines. Every PR gets code review — we read every line of hooks and scripts.

When submitting an external skill, include attribution in the plugin's README: where it came from (link to the original repo or author) and any modifications you made. See the [humanizer README](plugins/humanizer/README.md) for an example.

Once merged, the skill is available to all Trail of Bits employees and anyone else using this marketplace.

## License

This work is licensed under a [Creative Commons Attribution-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-sa/4.0/).
