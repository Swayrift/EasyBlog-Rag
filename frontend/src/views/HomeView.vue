<script setup>
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '@/api/client'
import PostCard from '@/components/PostCard.vue'

const posts = ref([])
const total = ref(0)
const health = ref(null)
const about = ref(null)
const tags = ref([])
const loading = ref(true)
const error = ref('')

onMounted(async () => {
  try {
    const [postsRes, healthRes] = await Promise.all([
      api.posts({ page: 1, pageSize: 4 }),
      api.health(),
    ])
    posts.value = postsRes.items
    total.value = postsRes.total
    health.value = healthRes
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }

  // 次要数据：失败不影响页面主体
  api.about().then((res) => (about.value = res)).catch(() => {})
  api.tags().then((res) => (tags.value = res)).catch(() => {})
})
</script>

<template>
  <div class="home">
  <!-- 单根元素包裹：App.vue 的 <Transition mode="out-in"> 要求视图为单元素根，
       fragment 根（包括顶层注释）会导致路由切换后新视图无法挂载（整页空白，刷新才恢复）。勿删。 -->
  <!-- ======= Hero ======= -->
  <section class="hero container">
    <div class="hero-side" aria-hidden="true">
      <span class="hero-side-line"></span>
      <span class="hero-side-text">记录 · 思考 · 分享</span>
    </div>

    <p class="eyebrow reveal">FastAPI / RAG / Vue</p>

    <h1 class="hero-title">
      <span class="reveal" style="--reveal-delay: 90ms">追风赶月莫停留</span><br>
      <span class="reveal grad-text" style="--reveal-delay: 200ms">平芜尽处是春山</span>
    </h1>

    <p class="hero-sub reveal" style="--reveal-delay: 320ms">
      你好啊，我的朋友。我是邃梨，这里是我的个人博客。
      这个博客用来记录我的所学所想，你可以在这里看到我发布的文章，也可以通过内置的问答系统，向我的知识库提问。
    </p>

    <div class="hero-actions reveal" style="--reveal-delay: 430ms">
      <RouterLink to="/articles" class="btn btn-primary">阅读文章</RouterLink>
      <RouterLink to="/chat" class="btn btn-ghost">向知识库提问</RouterLink>
      <span class="hero-status">
        <span class="dot" :class="health && health.vector_store_ok ? 'dot-on' : 'dot-off'"></span>
        {{
          loading
            ? '正在连接后端…'
            : health && health.vector_store_ok
              ? '知识库在线'
              : '知识库离线'
        }}
      </span>
    </div>
  </section>

  <!-- ======= 个人简介 ======= -->
  <section class="container intro-wrap">
    <div class="intro">
      <div class="intro-badge" aria-hidden="true">SR</div>
      <div class="intro-body">
        <p class="intro-name">
          {{ about?.name || 'SuiLi' }}
          <span class="intro-role">博客作者</span>
        </p>
        <p class="intro-summary">
          {{ about?.summary || '……' }}
        </p>
      </div>
      <RouterLink to="/about" class="btn btn-ghost intro-more">
        关于我 <span aria-hidden="true">→</span>
      </RouterLink>
    </div>
  </section>

  <!-- ======= 最新文章 ======= -->
  <section class="latest container">
    <div class="section-head reveal">
      <div>
        <p class="eyebrow">Latest</p>
        <h2 class="section-title">最新文章</h2>
      </div>
      <RouterLink to="/articles" class="section-more">
        全部文章 <span aria-hidden="true">→</span>
      </RouterLink>
    </div>

    <p v-if="loading" class="notice reveal">正在加载文章…</p>
    <p v-else-if="error" class="notice notice-error reveal">
      加载失败：{{ error }}（请确认后端服务已启动）
    </p>
    <div v-else-if="posts.length" class="post-list">
      <PostCard
        v-for="(post, i) in posts"
        :key="post.id"
        :post="post"
        :index="i"
        v-reveal="i * 110"
      />
    </div>
    <p v-else class="notice reveal">还没有文章。</p>
  </section>

  <!-- ======= 标签入口 ======= -->
  <section v-if="tags.length" class="container tags-section">
    <div class="section-head reveal">
      <div>
        <p class="eyebrow">Tags</p>
        <h2 class="section-title">按标签浏览</h2>
      </div>
    </div>
    <div class="home-tags">
      <RouterLink
        v-for="(tag, i) in tags"
        :key="tag.id"
        :to="`/articles?tag=${encodeURIComponent(tag.name)}`"
        class="home-tag reveal"
        :style="{ '--reveal-delay': `${i * 90}ms` }"
      >
        {{ tag.name }}
        <span class="home-tag-count">{{ tag.post_count }}</span>
      </RouterLink>
    </div>
  </section>

  <!-- ======= 问答引导 ======= -->
  <section class="container">
    <RouterLink to="/chat" class="ask-banner reveal">
      <div class="ask-glow" aria-hidden="true"></div>
      <div class="ask-text">
        <p class="ask-eyebrow">RAG Knowledge QA</p>
        <p class="ask-title">有问题？直接向知识库提问。</p>
        <p class="ask-sub">
          基于 BGE-M3 向量检索与 BGE-Reranker 重排，从文章与文档中找到答案并附带引用来源。
        </p>
      </div>
      <span class="ask-arrow" aria-hidden="true">→</span>
    </RouterLink>
  </section>
  </div>
</template>

<style scoped>
/* ---------- Hero ---------- */
.hero {
  position: relative;
  padding-top: calc(var(--nav-h) + 110px);
  padding-bottom: 110px;
}

.hero-side {
  position: absolute;
  right: 0;
  top: calc(var(--nav-h) + 140px);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 18px;
}

.hero-side-line {
  width: 1px;
  height: 120px;
  background: linear-gradient(180deg, var(--orange), transparent);
  animation: line-grow 1.4s cubic-bezier(0.22, 0.61, 0.36, 1) both;
}

@keyframes line-grow {
  from {
    transform: scaleY(0);
    transform-origin: top;
  }
  to {
    transform: scaleY(1);
    transform-origin: top;
  }
}

.hero-side-text {
  writing-mode: vertical-rl;
  font-family: var(--font-serif);
  font-size: 0.9rem;
  letter-spacing: 0.5em;
  color: var(--faint);
}

.hero-title {
  font-family: var(--font-serif);
  font-weight: 900;
  font-size: clamp(2.6rem, 6.4vw, 4.8rem);
  line-height: 1.22;
  margin-top: 26px;
  letter-spacing: 0.01em;
}

.hero-sub {
  margin-top: 30px;
  max-width: 560px;
  color: var(--muted);
  font-size: 1.02rem;
  line-height: 2;
}

.hero-actions {
  margin-top: 44px;
  display: flex;
  align-items: center;
  gap: 18px;
  flex-wrap: wrap;
}

.hero-status {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  margin-left: 10px;
  font-family: var(--font-mono);
  font-size: 0.74rem;
  letter-spacing: 0.12em;
  color: var(--muted);
}

/* ---------- 个人简介 ---------- */
.intro-wrap {
  padding-bottom: 96px;
}

.intro {
  display: flex;
  align-items: center;
  gap: 26px;
  padding: 30px 34px;
  border: 1px solid var(--line);
  border-radius: 18px;
  background:
    linear-gradient(120deg, rgba(255, 122, 26, 0.07), rgba(255, 122, 26, 0) 46%),
    var(--bg-soft);
  transition: border-color 0.3s ease, box-shadow 0.35s ease, transform 0.35s cubic-bezier(0.22, 0.61, 0.36, 1);
}

.intro:hover {
  border-color: rgba(255, 122, 26, 0.4);
  box-shadow: 0 22px 48px -26px rgba(255, 122, 26, 0.4);
  transform: translateY(-3px);
}

.intro-badge {
  flex: none;
  width: 62px;
  height: 62px;
  border-radius: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-mono);
  font-weight: 600;
  font-style: italic;
  font-size: 1.25rem;
  color: #1c0d02;
  background: var(--grad);
  box-shadow: 0 12px 28px -12px rgba(255, 122, 26, 0.65);
}

.intro-body {
  flex: 1;
  min-width: 0;
}

.intro-name {
  font-family: var(--font-serif);
  font-weight: 900;
  font-size: 1.28rem;
  display: flex;
  align-items: baseline;
  gap: 12px;
  flex-wrap: wrap;
}

.intro-role {
  font-family: var(--font-mono);
  font-size: 0.68rem;
  font-weight: 400;
  letter-spacing: 0.22em;
  color: var(--orange-hi);
  border: 1px solid rgba(255, 122, 26, 0.4);
  border-radius: 999px;
  padding: 3px 10px;
}

.intro-summary {
  margin-top: 8px;
  color: var(--muted);
  font-size: 0.92rem;
  line-height: 1.8;
}

.intro-more {
  flex: none;
}

/* ---------- 最新文章 ---------- */
.latest {
  padding-bottom: 90px;
}

.section-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 34px;
}

.section-title {
  font-family: var(--font-serif);
  font-weight: 900;
  font-size: 1.9rem;
  margin-top: 12px;
}

.section-more {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  letter-spacing: 0.1em;
  color: var(--muted);
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding-bottom: 6px;
  transition: color 0.25s ease;
}

.section-more span {
  transition: transform 0.3s cubic-bezier(0.22, 0.61, 0.36, 1);
}

.section-more:hover {
  color: var(--orange-hi);
}

.section-more:hover span {
  transform: translateX(6px);
}

.post-list {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

/* ---------- 标签入口 ---------- */
.tags-section {
  padding-bottom: 90px;
}

.home-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.home-tag {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  padding: 10px 20px;
  border: 1px solid var(--line-strong);
  border-radius: 999px;
  font-size: 0.9rem;
  color: var(--text);
  background: rgba(255, 255, 255, 0.02);
  transition: all 0.28s ease;
}

.home-tag:hover {
  border-color: rgba(255, 122, 26, 0.6);
  color: var(--orange-hi);
  background: rgba(255, 122, 26, 0.07);
  transform: translateY(-2px);
  box-shadow: 0 12px 26px -16px rgba(255, 122, 26, 0.55);
}

.home-tag-count {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--faint);
  transition: color 0.28s ease;
}

.home-tag:hover .home-tag-count {
  color: var(--orange);
}

/* ---------- 问答引导 ---------- */
.ask-banner {
  position: relative;
  display: flex;
  align-items: center;
  gap: 30px;
  padding: 44px 46px;
  border: 1px solid rgba(255, 122, 26, 0.3);
  border-radius: 20px;
  background: linear-gradient(140deg, rgba(255, 122, 26, 0.09), rgba(255, 77, 0, 0.02) 55%), var(--bg-soft);
  overflow: hidden;
  transition: transform 0.35s cubic-bezier(0.22, 0.61, 0.36, 1), border-color 0.3s ease, box-shadow 0.35s ease;
}

.ask-banner:hover {
  transform: translateY(-4px);
  border-color: rgba(255, 122, 26, 0.6);
  box-shadow: 0 30px 60px -30px rgba(255, 122, 26, 0.4);
}

.ask-glow {
  position: absolute;
  width: 340px;
  height: 340px;
  right: -80px;
  top: -140px;
  background: radial-gradient(circle, rgba(255, 122, 26, 0.22), transparent 65%);
  filter: blur(10px);
  pointer-events: none;
  transition: transform 0.6s ease;
}

.ask-banner:hover .ask-glow {
  transform: scale(1.15);
}

.ask-text {
  position: relative;
  flex: 1;
}

.ask-eyebrow {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  letter-spacing: 0.3em;
  color: var(--orange);
  margin-bottom: 12px;
}

.ask-title {
  font-family: var(--font-serif);
  font-weight: 900;
  font-size: 1.7rem;
  margin-bottom: 10px;
}

.ask-sub {
  color: var(--muted);
  font-size: 0.92rem;
  max-width: 520px;
}

.ask-arrow {
  position: relative;
  font-size: 2rem;
  color: var(--orange);
  transition: transform 0.35s cubic-bezier(0.22, 0.61, 0.36, 1);
}

.ask-banner:hover .ask-arrow {
  transform: translateX(10px);
}

@media (max-width: 900px) {
  .hero-side {
    display: none;
  }
}

@media (max-width: 640px) {
  .hero {
    padding-top: calc(var(--nav-h) + 70px);
    padding-bottom: 70px;
  }
  .intro {
    flex-direction: column;
    align-items: flex-start;
    gap: 18px;
    padding: 26px 22px;
  }
  .ask-banner {
    padding: 32px 26px;
  }
  .ask-arrow {
    display: none;
  }
}
</style>
