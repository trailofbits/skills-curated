# Component Reference

## Document

Root component representing the PDF document.

| Prop         | Type     | Default | Description                                                                                  |
| ------------ | -------- | ------- | -------------------------------------------------------------------------------------------- |
| `title`      | string   | -       | Document title metadata                                                                      |
| `author`     | string   | -       | Document author metadata                                                                     |
| `subject`    | string   | -       | Document subject metadata                                                                    |
| `keywords`   | string   | -       | Document keywords metadata                                                                   |
| `creator`    | string   | -       | Application that created the document                                                        |
| `producer`   | string   | -       | PDF producer                                                                                 |
| `pdfVersion` | string   | "1.3"   | PDF version                                                                                  |
| `language`   | string   | -       | Default document language                                                                    |
| `pageMode`   | string   | -       | Display mode: useNone, useOutlines, useThumbs, fullScreen, useOC, useAttachments             |
| `pageLayout` | string   | -       | Page layout: singlePage, oneColumn, twoColumnLeft, twoColumnRight, twoPageLeft, twoPageRight |
| `onRender`   | function | -       | Callback after rendering with `{ blob }`                                                     |

## Page

Represents a single page in the document.

| Prop          | Type                | Default    | Description                                                               |
| ------------- | ------------------- | ---------- | ------------------------------------------------------------------------- |
| `size`        | string/array/object | "A4"       | Page size (A4, Letter, Legal, etc.) or [width, height] or {width, height} |
| `orientation` | string              | "portrait" | Page orientation: portrait, landscape                                     |
| `wrap`        | boolean             | true       | Enable automatic page wrapping                                            |
| `style`       | object/array        | -          | Page styling                                                              |
| `debug`       | boolean             | false      | Show bounding box                                                         |
| `dpi`         | number              | 72         | Custom DPI setting                                                        |
| `id`          | string              | -          | Destination ID for internal links                                         |

## View

Container component for layout, similar to div.

| Prop               | Type         | Default | Description                                                                                  |
| ------------------ | ------------ | ------- | -------------------------------------------------------------------------------------------- |
| `wrap`             | boolean      | true    | Enable page wrapping                                                                         |
| `style`            | object/array | -       | View styling                                                                                 |
| `render`           | function     | -       | Dynamic content: `({ pageNumber, totalPages, subPageNumber, subPageTotalPages }) => content` |
| `debug`            | boolean      | false   | Show bounding box                                                                            |
| `fixed`            | boolean      | false   | Render on all wrapped pages                                                                  |
| `break`            | boolean      | false   | Force page break before this element                                                         |
| `minPresenceAhead` | number       | -       | Minimum space ahead before breaking                                                          |
| `id`               | string       | -       | Destination ID for internal links                                                            |

## Text

Displays text content.

| Prop                  | Type         | Default | Description                     |
| --------------------- | ------------ | ------- | ------------------------------- |
| `wrap`                | boolean      | true    | Enable page wrapping            |
| `style`               | object/array | -       | Text styling                    |
| `render`              | function     | -       | Dynamic content function        |
| `debug`               | boolean      | false   | Show bounding box               |
| `fixed`               | boolean      | false   | Render on all wrapped pages     |
| `hyphenationCallback` | function     | -       | Custom hyphenation              |
| `orphans`             | number       | -       | Minimum lines at bottom of page |
| `widows`              | number       | -       | Minimum lines at top of page    |
| `id`                  | string       | -       | Destination ID                  |

## Link

Creates hyperlinks.

| Prop    | Type         | Default | Description                                 |
| ------- | ------------ | ------- | ------------------------------------------- |
| `src`   | string       | -       | URL or internal destination (prefix with #) |
| `wrap`  | boolean      | true    | Enable page wrapping                        |
| `style` | object/array | -       | Link styling                                |
| `debug` | boolean      | false   | Show bounding box                           |

## Image

Displays images.

| Prop             | Type                   | Default | Description                                             |
| ---------------- | ---------------------- | ------- | ------------------------------------------------------- |
| `src` / `source` | string/object/function | -       | Image source: URL, file path, Buffer, or async function |
| `style`          | object/array           | -       | Image styling                                           |
| `debug`          | boolean                | false   | Show bounding box                                       |
| `cache`          | boolean                | true    | Enable image caching                                    |

## Note

Adds annotation notes.

| Prop       | Type         | Default | Description       |
| ---------- | ------------ | ------- | ----------------- |
| `children` | string       | -       | Note text content |
| `style`    | object/array | -       | Note styling      |

## Canvas

Freeform drawing component.

| Prop    | Type         | Default | Description                                          |
| ------- | ------------ | ------- | ---------------------------------------------------- |
| `paint` | function     | -       | Painter function: `(painter, width, height) => void` |
| `style` | object/array | -       | Canvas styling                                       |
| `debug` | boolean      | false   | Show bounding box                                    |

## Svg

SVG container component.

| Prop                  | Type          | Default | Description           |
| --------------------- | ------------- | ------- | --------------------- |
| `width`               | string/number | -       | SVG width             |
| `height`              | string/number | -       | SVG height            |
| `viewBox`             | string        | -       | SVG viewBox           |
| `preserveAspectRatio` | string        | -       | Aspect ratio handling |
| `style`               | object/array  | -       | SVG styling           |

### SVG Shape Elements

| Element          | Key Props                                 |
| ---------------- | ----------------------------------------- |
| `Line`           | x1, y1, x2, y2, stroke, strokeWidth       |
| `Rect`           | x, y, width, height, rx, ry, fill, stroke |
| `Circle`         | cx, cy, r, fill, stroke                   |
| `Ellipse`        | cx, cy, rx, ry, fill, stroke              |
| `Polygon`        | points, fill, stroke                      |
| `Polyline`       | points, fill, stroke                      |
| `Path`           | d, fill, stroke                           |
| `Text`           | x, y, fill, textAnchor                    |
| `Tspan`          | x, y, dx, dy                              |
| `G`              | transform (group container)               |
| `Defs`           | (definitions container)                   |
| `ClipPath`       | id (clipping path)                        |
| `LinearGradient` | id, x1, y1, x2, y2                        |
| `RadialGradient` | id, cx, cy, r, fx, fy                     |
| `Stop`           | offset, stopColor, stopOpacity            |

### SVG Presentation Attributes

`color`, `dominantBaseline`, `fill`, `fillOpacity`, `fillRule`, `opacity`, `stroke`, `strokeWidth`,
`strokeOpacity`, `strokeLinecap`, `strokeLinejoin`, `strokeDasharray`, `transform`, `textAnchor`,
`visibility`

## Supported CSS Properties

### Flexbox

`alignContent`, `alignItems`, `alignSelf`, `flex`, `flexDirection`, `flexWrap`, `flexFlow`,
`flexGrow`, `flexShrink`, `flexBasis`, `justifyContent`, `gap`, `rowGap`, `columnGap`

### Layout

`bottom`, `display`, `left`, `position`, `right`, `top`, `overflow`, `zIndex`

### Dimensions

`height`, `maxHeight`, `maxWidth`, `minHeight`, `minWidth`, `width`

### Color

`backgroundColor`, `color`, `opacity`

### Text

`fontSize`, `fontFamily`, `fontStyle`, `fontWeight`, `letterSpacing`, `lineHeight`, `maxLines`,
`textAlign`, `textDecoration`, `textDecorationColor`, `textDecorationStyle`, `textIndent`,
`textOverflow`, `textTransform`

### Margins

`margin`, `marginTop`, `marginRight`, `marginBottom`, `marginLeft`, `marginHorizontal`,
`marginVertical`

### Padding

`padding`, `paddingTop`, `paddingRight`, `paddingBottom`, `paddingLeft`, `paddingHorizontal`,
`paddingVertical`

### Borders

`border`, `borderTop`, `borderRight`, `borderBottom`, `borderLeft`, `borderColor`, `borderTopColor`,
`borderRightColor`, `borderBottomColor`, `borderLeftColor`, `borderStyle`, `borderTopStyle`,
`borderRightStyle`, `borderBottomStyle`, `borderLeftStyle`, `borderWidth`, `borderTopWidth`,
`borderRightWidth`, `borderBottomWidth`, `borderLeftWidth`, `borderRadius`, `borderTopLeftRadius`,
`borderTopRightRadius`, `borderBottomRightRadius`, `borderBottomLeftRadius`

### Transformations

`rotate`, `scale`, `scaleX`, `scaleY`, `translate`, `translateX`, `translateY`, `skew`, `skewX`,
`skewY`, `matrix`, `transformOrigin`

### Object Fit

`objectFit`, `objectPosition`
