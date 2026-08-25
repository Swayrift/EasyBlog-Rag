<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/api/client'
import MarkdownView from '@/components/MarkdownView.vue'

const route = useRoute()
const router = useRouter()

const post = ref(null)
const loading = ref(true)
const error = ref('')

function goBack() {
  // 有历史则返回上一页，否则回到文章列表
  if (window.history.state && window.history.state.back) {
    router.back()
  } else {
    router.push('/articles')
  }
}

function formatDate(value) {
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return ''
  return `${d.getFullYear()} 年 ${d.getMonth() + 1} 月 ${d.getDate()} 日`
}

onMounted(async () => {
  try {
    post.value = await api.post(route.params.slug)
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <article class="post">
    <p v-if="loading" class="container-read notice">正在加载文章…</p>

    <template v-else-if="error">
      <div class="container-read notice notice-error">
        <p>{{ error }}</p>
        <button class="btn btn-ghost" type="button" @click="goBack">返回文章列表</button>
      </div>
    </template>

    <template v-else-if="post">
      <header class="container-read post-head">
        <div class="post-meta-row reveal">
          <time class="post-date">{{ formatDate(post.created_at) }}</time>
          <span v-for="tag in post.tags" :key="tag" class="chip chip-hot">{{ tag }}</span>
        </div>
        <h1 class="post-title reveal" style="--reveal-delay: 100ms">{{ post.title }}</h1>
        <p v-if="post.summary" class="post-lead reveal" style="--reveal-delay: 200ms">
          {{ post.summary }}
        </p>
        <div class="post-rule reveal" style="--reveal-delay: 280ms" aria-hidden="true"></div>
      </header>

      <div class="container-read post-content reveal" style="--reveal-delay: 340ms">
        <MarkdownView :source="post.content_md" />
      </div>

      <footer class="container-read post-foot reveal">
        <p class="post-foot-text">— 全文完 —</p>
        <button class="btn btn-ghost" type="button" @click="goBack">返回</button>
      </footer>
    </template>
  </article>
</template>

<style scoped>
.post {
  min-height: 100vh;
  padding-bottom: 90px;
}

.post-head {
  padding-top: calc(var(--nav-h) + 46px);
}

.post-meta-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.post-date {
  font-family: var(--font-mono);
  font-size: 0.76rem;
  letter-spacing: 0.12em;
  color: var(--faint);
}

.post-title {
  font-family: var(--font-serif);
  font-weight: 900;
  font-size: clamp(1.9rem, 4.6vw, 2.9rem);
  line-height: 1.35;
  margin-top: 22px;
}

.post-lead {
  margin-top: 20px;
  color: var(--muted);
  font-size: 1.02rem;
  line-height: 1.95;
}

.post-rule {
  margin-top: 36px;
  height: 1px;
  background: linear-gradient(90deg, var(--orange), rgba(255, 122, 26, 0.25) 45%, transparent);
}

.post-content {
  padding-top: 44px;
}

.post-foot {
  margin-top: 72px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 22px;
}

.post-foot-text {
  font-family: var(--font-mono);
  font-size: 0.76rem;
  letter-spacing: 0.3em;
  color: var(--faint);
}
</style>
