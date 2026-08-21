<script setup>
import { computed } from 'vue'
import { marked } from 'marked'

marked.use({ gfm: true, breaks: true })

const props = defineProps({
  source: { type: String, default: '' },
})

const html = computed(() => marked.parse(props.source || ''))
</script>

<template>
  <!-- 内容来自本地 Markdown 文件（作者本人维护），直接渲染 -->
  <div class="md-body" v-html="html"></div>
</template>

<style>
.md-body {
  color: var(--text);
  font-size: 1rem;
  line-height: 1.9;
  word-break: break-word;
}

.md-body > * + * {
  margin-top: 1.1em;
}

.md-body h1,
.md-body h2,
.md-body h3,
.md-body h4 {
  font-family: var(--font-serif);
  font-weight: 900;
  line-height: 1.4;
  margin-top: 2em;
}

.md-body h1 {
  font-size: 1.7rem;
}
.md-body h2 {
  font-size: 1.4rem;
  display: flex;
  align-items: center;
  gap: 12px;
}
.md-body h2::before {
  content: '';
  width: 8px;
  height: 8px;
  border-radius: 2px;
  background: var(--grad);
  transform: rotate(45deg);
  flex: none;
}
.md-body h3 {
  font-size: 1.18rem;
}

.md-body p {
  color: #ddd2c4;
}

.md-body a {
  color: var(--orange-hi);
  text-decoration: underline;
  text-decoration-color: rgba(255, 122, 26, 0.4);
  text-underline-offset: 4px;
  transition: text-decoration-color 0.25s ease, color 0.25s ease;
}

.md-body a:hover {
  color: #ffc46b;
  text-decoration-color: #ffc46b;
}

.md-body strong {
  color: var(--text);
  font-weight: 700;
}

.md-body ul,
.md-body ol {
  padding-left: 1.4em;
  color: #ddd2c4;
}

.md-body li + li {
  margin-top: 0.45em;
}

.md-body li::marker {
  color: var(--orange);
  font-family: var(--font-mono);
}

.md-body blockquote {
  border-left: 3px solid;
  border-image: var(--grad) 1;
  background: rgba(255, 122, 26, 0.05);
  padding: 14px 20px;
  border-radius: 0 10px 10px 0;
  color: var(--muted);
}

.md-body code {
  font-family: var(--font-mono);
  font-size: 0.86em;
  background: rgba(255, 162, 77, 0.1);
  border: 1px solid rgba(255, 162, 77, 0.18);
  color: #ffc46b;
  padding: 2px 7px;
  border-radius: 6px;
}

.md-body pre {
  background: #0d0a08;
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 18px 20px;
  overflow-x: auto;
  position: relative;
}

.md-body pre::before {
  content: '';
  position: absolute;
  top: 0;
  left: 16px;
  right: 16px;
  height: 1px;
  background: var(--grad);
  opacity: 0.5;
}

.md-body pre code {
  background: none;
  border: none;
  padding: 0;
  color: #e8dccb;
  font-size: 0.85rem;
  line-height: 1.7;
}

.md-body hr {
  border: none;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--line-strong), transparent);
  margin-block: 2.4em;
}

.md-body img {
  max-width: 100%;
  border-radius: 12px;
  border: 1px solid var(--line);
}

.md-body table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.md-body th,
.md-body td {
  border: 1px solid var(--line);
  padding: 9px 14px;
  text-align: left;
}

.md-body th {
  background: rgba(255, 122, 26, 0.07);
  color: var(--orange-hi);
  font-weight: 600;
}
</style>
