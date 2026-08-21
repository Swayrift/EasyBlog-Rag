<script setup>
import { onMounted, ref } from 'vue'
import { api } from '@/api/client'
import MarkdownView from '@/components/MarkdownView.vue'

const about = ref(null)
const loading = ref(true)
const error = ref('')

const contactIcons = {
  email: '@',
  github: 'GH',
}

function contactHref(key, value) {
  if (key === 'email') return `mailto:${value}`
  return value
}

onMounted(async () => {
  try {
    about.value = await api.about()
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <section class="about container">
    <header class="about-head">
      <p class="eyebrow reveal">About</p>
      <h1 class="about-name reveal" style="--reveal-delay: 90ms">
        {{ about?.name || '关于我' }}
      </h1>
      <p v-if="about?.summary" class="about-summary reveal" style="--reveal-delay: 180ms">
        {{ about.summary }}
      </p>
    </header>

    <p v-if="loading" class="notice">正在加载…</p>
    <p v-else-if="error" class="notice notice-error">
      加载失败：{{ error }}（请确认后端服务已启动）
    </p>

    <template v-else-if="about">
      <!-- 技术栈 -->
      <div v-if="about.tech_stack.length" class="about-block reveal" style="--reveal-delay: 260ms">
        <p class="about-label">技术栈</p>
        <div class="tech-row">
          <span v-for="(tech, i) in about.tech_stack" :key="tech" class="tech-chip">
            <span class="tech-index">{{ String(i + 1).padStart(2, '0') }}</span>
            {{ tech }}
          </span>
        </div>
      </div>

      <!-- 联系方式 -->
      <div
        v-if="about.contact && Object.keys(about.contact).length"
        class="about-block reveal"
        style="--reveal-delay: 340ms"
      >
        <p class="about-label">联系方式</p>
        <div class="contact-row">
          <a
            v-for="(value, key) in about.contact"
            :key="key"
            :href="contactHref(key, value)"
            class="contact-link"
            target="_blank"
            rel="noopener"
          >
            <span class="contact-icon">{{ contactIcons[key] || '∞' }}</span>
            <span class="contact-key">{{ key }}</span>
            <span class="contact-value">{{ value }}</span>
          </a>
        </div>
      </div>

      <!-- 正文 -->
      <div v-if="about.content_md" class="about-content reveal" style="--reveal-delay: 420ms">
        <div class="about-rule" aria-hidden="true"></div>
        <MarkdownView :source="about.content_md" />
      </div>
    </template>
  </section>
</template>

<style scoped>
.about {
  padding-top: calc(var(--nav-h) + 84px);
  min-height: 70vh;
  max-width: 780px;
}

.about-name {
  font-family: var(--font-serif);
  font-weight: 900;
  font-size: clamp(2.4rem, 5.4vw, 3.4rem);
  margin-top: 18px;
  background: var(--grad);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  display: inline-block;
}

.about-summary {
  margin-top: 18px;
  color: var(--muted);
  font-size: 1.05rem;
  line-height: 1.9;
}

.about-block {
  margin-top: 44px;
}

.about-label {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  letter-spacing: 0.3em;
  color: var(--faint);
  margin-bottom: 16px;
}

.tech-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.tech-chip {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  padding: 9px 16px;
  border: 1px solid var(--line-strong);
  border-radius: 10px;
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: var(--text);
  background: rgba(255, 255, 255, 0.02);
  transition: all 0.28s ease;
}

.tech-chip:hover {
  border-color: rgba(255, 122, 26, 0.55);
  transform: translateY(-2px);
  box-shadow: 0 10px 24px -14px rgba(255, 122, 26, 0.5);
}

.tech-index {
  color: var(--orange);
  font-style: italic;
}

.contact-row {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.contact-link {
  display: inline-flex;
  align-items: center;
  gap: 14px;
  padding: 13px 18px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--bg-soft);
  transition: all 0.28s ease;
}

.contact-link:hover {
  border-color: rgba(255, 122, 26, 0.5);
  transform: translateX(4px);
}

.contact-icon {
  width: 34px;
  height: 34px;
  flex: none;
  border-radius: 9px;
  background: var(--grad-soft);
  border: 1px solid rgba(255, 122, 26, 0.3);
  color: var(--orange-hi);
  font-family: var(--font-mono);
  font-size: 0.78rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.contact-key {
  font-family: var(--font-mono);
  font-size: 0.78rem;
  color: var(--faint);
  letter-spacing: 0.08em;
}

.contact-value {
  margin-left: auto;
  font-size: 0.88rem;
  color: var(--muted);
  transition: color 0.25s ease;
}

.contact-link:hover .contact-value {
  color: var(--orange-hi);
}

.about-content {
  margin-top: 52px;
}

.about-rule {
  height: 1px;
  background: linear-gradient(90deg, var(--orange), rgba(255, 122, 26, 0.25) 45%, transparent);
  margin-bottom: 36px;
}
</style>
