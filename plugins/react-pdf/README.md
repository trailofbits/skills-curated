# React-PDF

Generates PDF documents using the React-PDF library (`@react-pdf/renderer`) with TypeScript and JSX. Supports flexbox layout, SVG graphics, custom Google Fonts, emoji, and professional typesetting with Knuth-Plass line breaking.

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
