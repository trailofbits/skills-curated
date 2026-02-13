# React-PDF

Generates PDF documents using the React-PDF library (`@react-pdf/renderer`) with TypeScript and JSX. Supports flexbox layout, SVG graphics, custom Google Fonts, emoji, and professional typesetting with Knuth-Plass line breaking.

## Why React-PDF over Python PDF Libraries?

Libraries like ReportLab, WeasyPrint, or fpdf2 work, but React-PDF has real advantages for AI-generated documents:

- **Flexbox & grid layout** — powered by Yoga (Facebook's layout engine). Centering, columns, wrapping grids — it just works. No absolute coordinate math.
- **SVG primitives** — `<Svg>`, `<Path>`, `<Circle>` are first-class components. Draw charts and icons inline without a separate graphics library.
- **Component composition** — build PDFs like React components. Reusable headers, tables, cards — all composable with props. Declarative, not imperative.
- **Google Fonts support** — register any TrueType font with `Font.register()`. The skill bundles a reference of ~65 popular Google Fonts with direct download URLs.
- **Knuth-Plass line breaking** — the same algorithm used by TeX. Produces professionally typeset paragraphs with proper hyphenation.
- **Smart page breaks** — `wrap`, `break`, `minPresenceAhead` control content flow across pages declaratively. Orphan/widow control built in.
- **Emoji support** — register Twemoji assets and use emoji directly in text. No custom rendering logic needed.

## Install

```
/plugin install trailofbits/skills-curated/plugins/react-pdf
```

## Prerequisites

- Node.js 18+
- `npm install react @react-pdf/renderer`
- `npm install -D tsx @types/react`

## What It Covers

- Core components (Document, Page, View, Text, Image, Link, Svg, Canvas)
- Flexbox layout and styling (StyleSheet, units, common properties)
- Custom fonts (Google Fonts reference with ~65 font families and download URLs)
- SVG graphics and icon conversion
- Fixed headers/footers and page numbers
- Page breaks, wrapping, orphan/widow control
- Emoji rendering via Twemoji
- PDF preview with pdftoppm or PyMuPDF

## Key Files

- `references/components.md` — Full component API reference and CSS properties
- `references/google-fonts.txt` — ~65 Google Fonts with TrueType download URLs
- `assets/example-template.tsx` — Working example with footers, page numbers, cards

## Credits

- **Source:** [molefrog/skills](https://github.com/molefrog/skills)
- **Author:** molefrog
- **License:** MIT
