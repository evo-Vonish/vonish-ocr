<template>
  <div class="md-render" v-html="renderedHtml" />
</template>

<script setup>
import { computed } from 'vue'
import { marked } from 'marked'
import katex from 'katex'

const props = defineProps({
  text: { type: String, default: '' },
})

/** Escaped brackets → real brackets  (AI often returns \\( \\[ \\) \\] escaped) */
function unescapeMath(t) {
  return t
    .replace(/\\\$/g, '$')
    .replace(/\\\\\(/g, '\\(')
    .replace(/\\\\\)/g, '\\)')
    .replace(/\\\\\[/g, '\\[')
    .replace(/\\\\\]/g, '\\]')
}

/** Render $$...$$ and $...$ with KaTeX before Markdown touches them */
function renderMath(md) {
  // Block math: $$ ... $$
  md = md.replace(/\$\$([\s\S]*?)\$\$/g, (_m, math) => {
    try {
      return katex.renderToString(math.trim(), { displayMode: true, throwOnError: false })
    } catch (e) {
      return `<pre class="katex-error">${_m}</pre>`
    }
  })
  // Inline math: $ ... $
  md = md.replace(/(?<!\$)\$(?!\$)([^$]+)\$(?!\$)/g, (_m, math) => {
    try {
      return katex.renderToString(math.trim(), { displayMode: false, throwOnError: false })
    } catch (e) {
      return `<span class="katex-error">${_m}</span>`
    }
  })
  return md
}

const renderedHtml = computed(() => {
  if (!props.text) return ''
  let processed = unescapeMath(props.text)
  processed = renderMath(processed)
  // Use marked with gfm tables, no raw HTML
  return marked.parse(processed, { breaks: true, gfm: true }) || ''
})
</script>

<style>
/* KaTeX font imports */
@import 'katex/dist/katex.min.css';

/* ── Markdown rendered content ── */
.md-render {
  font-family: var(--font-body);
  font-size: var(--fs-body);
  line-height: 1.85;
  color: var(--v-text);
  word-break: break-word;
}

.md-render p {
  margin: 0 0 var(--s3);
}

.md-render p:last-child {
  margin-bottom: 0;
}

/* headings */
.md-render h1, .md-render h2, .md-render h3, .md-render h4 {
  font-family: var(--font-title);
  color: var(--v-paper);
  margin: var(--s4) 0 var(--s2);
  line-height: 1.3;
}

.md-render h1 { font-size: var(--fs-h1); font-weight: var(--fw-bold); }
.md-render h2 { font-size: calc(var(--fs-h1) * 0.85); font-weight: var(--fw-semibold); }
.md-render h3 { font-size: var(--fs-h2); font-weight: var(--fw-semibold); }
.md-render h4 { font-size: var(--fs-body); font-weight: var(--fw-semibold); }

/* inline code */
.md-render code {
  font-family: var(--font-mono);
  font-size: 0.9em;
  color: var(--v-accent);
  background: var(--v-rail);
  padding: 1px 6px;
  border-radius: 3px;
}

/* code blocks */
.md-render pre {
  font-family: var(--font-mono);
  font-size: var(--fs-small);
  background: color-mix(in srgb, var(--v-coal) 90%, black);
  border: 1px solid var(--v-border);
  border-radius: var(--r3);
  padding: var(--s3);
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-word;
  margin: var(--s3) 0;
}

.md-render pre code {
  color: var(--v-text);
  background: none;
  padding: 0;
  border-radius: 0;
}

/* bold / italic */
.md-render strong { font-weight: var(--fw-semibold); color: var(--v-paper); }
.md-render em { font-style: italic; }

/* links */
.md-render a {
  color: var(--v-accent);
  text-decoration: none;
  border-bottom: 1px solid transparent;
  transition: border-color 0.15s;
}

.md-render a:hover { border-bottom-color: var(--v-accent); }

/* blockquote */
.md-render blockquote {
  margin: var(--s3) 0;
  padding: var(--s2) var(--s3);
  border-left: 2px solid var(--v-accent);
  background: var(--v-accent-08);
  border-radius: 0 var(--r2) var(--r2) 0;
  color: var(--v-text-muted);
  font-style: italic;
}

.md-render blockquote p { margin: 0; }

/* lists */
.md-render ul, .md-render ol {
  margin: var(--s2) 0;
  padding-left: var(--s5);
}

.md-render li {
  margin-bottom: var(--s1);
  line-height: 1.7;
}

.md-render li:last-child { margin-bottom: 0; }

/* horizontal rule */
.md-render hr {
  border: none;
  border-top: 1px solid var(--v-border);
  margin: var(--s4) 0;
}

/* tables */
.md-render table {
  width: 100%;
  border-collapse: collapse;
  margin: var(--s3) 0;
}

.md-render th {
  background: var(--v-rail);
  color: var(--v-paper);
  font-weight: var(--fw-semibold);
  font-size: var(--fs-caption);
  border-bottom: 2px solid var(--v-border);
  padding: var(--s2) var(--s3);
  text-align: left;
  font-family: var(--font-mono);
}

.md-render td {
  border-bottom: 1px solid var(--v-border);
  padding: var(--s2) var(--s3);
  color: var(--v-text-muted);
  font-size: var(--fs-small);
}

.md-render tr:hover td { background: var(--v-rail); }

/* KaTeX overrides for theme compatibility */
.md-render .katex { font-size: 1.1em; }
.md-render .katex .base,
.md-render .katex .mord { color: var(--v-text); }
.md-render .katex-error { color: var(--v-error); }

/* images */
.md-render img {
  max-width: 100%;
  border-radius: var(--r2);
  border: 1px solid var(--v-border);
}
</style>
