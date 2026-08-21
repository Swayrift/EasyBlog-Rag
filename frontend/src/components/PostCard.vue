<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

const props = defineProps({
  post: { type: Object, required: true },
  index: { type: Number, default: 0 },
})

const num = computed(() => String(props.index + 1).padStart(2, '0'))

const dateText = computed(() => {
  const d = new Date(props.post.created_at)
  if (Number.isNaN(d.getTime())) return ''
  return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, '0')}.${String(
    d.getDate(),
  ).padStart(2, '0')}`
})
</script>

<template>
  <RouterLink :to="`/posts/${post.slug}`" class="post-card">
    <span class="post-index" aria-hidden="true">{{ num }}</span>

    <div class="post-body">
      <h3 class="post-title">{{ post.title }}</h3>
      <p class="post-summary">{{ post.summary }}</p>
      <div class="post-meta">
        <span v-for="tag in post.tags" :key="tag" class="chip">{{ tag }}</span>
        <time class="post-date">{{ dateText }}</time>
      </div>
    </div>

    <span class="post-arrow" aria-hidden="true">→</span>
  </RouterLink>
</template>

<style scoped>
.post-card {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 26px;
  padding: 30px 32px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background:
    linear-gradient(160deg, rgba(255, 235, 214, 0.03), rgba(255, 235, 214, 0) 42%),
    var(--bg-soft);
  overflow: hidden;
  transition:
    transform 0.35s cubic-bezier(0.22, 0.61, 0.36, 1),
    border-color 0.35s ease,
    box-shadow 0.35s ease;
}

.post-card::before {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(560px 180px at 50% -30%, rgba(255, 122, 26, 0.16), transparent 65%);
  opacity: 0;
  transition: opacity 0.45s ease;
  pointer-events: none;
}

.post-card:hover {
  transform: translateY(-4px);
  border-color: rgba(255, 122, 26, 0.45);
  box-shadow: 0 24px 48px -24px rgba(255, 122, 26, 0.35);
}

.post-card:hover::before {
  opacity: 1;
}

.post-index {
  font-family: var(--font-mono);
  font-style: italic;
  font-size: 1.05rem;
  color: var(--faint);
  padding-top: 6px;
  transition: color 0.3s ease;
}

.post-card:hover .post-index {
  color: var(--orange);
}

.post-body {
  flex: 1;
  min-width: 0;
}

.post-title {
  font-family: var(--font-serif);
  font-size: 1.4rem;
  font-weight: 900;
  line-height: 1.4;
  margin-bottom: 10px;
  transition: color 0.3s ease;
}

.post-card:hover .post-title {
  background: var(--grad);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.post-summary {
  color: var(--muted);
  font-size: 0.92rem;
  line-height: 1.75;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 16px;
}

.post-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.post-date {
  margin-left: auto;
  font-family: var(--font-mono);
  font-size: 0.74rem;
  letter-spacing: 0.1em;
  color: var(--faint);
}

.post-arrow {
  align-self: center;
  font-size: 1.3rem;
  color: var(--faint);
  transition: transform 0.35s cubic-bezier(0.22, 0.61, 0.36, 1), color 0.3s ease;
}

.post-card:hover .post-arrow {
  transform: translateX(8px);
  color: var(--orange);
}

@media (max-width: 640px) {
  .post-card {
    padding: 22px 20px;
    gap: 16px;
  }
  .post-arrow {
    display: none;
  }
}
</style>
