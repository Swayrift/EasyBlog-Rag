<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '@/api/client'
import PostCard from '@/components/PostCard.vue'

const route = useRoute()

const PAGE_SIZE = 10

const posts = ref([])
const total = ref(0)
const page = ref(1)
const activeTag = ref('')
const tags = ref([])
const loading = ref(true)
const loadingMore = ref(false)
const error = ref('')

const hasMore = () => posts.value.length < total.value

function tagFromQuery() {
  return route.query.tag ? String(route.query.tag) : ''
}

async function fetchTags() {
  try {
    tags.value = await api.tags()
  } catch {
    tags.value = []
  }
}

async function loadFirstPage() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.posts({
      page: 1,
      pageSize: PAGE_SIZE,
      tag: activeTag.value || undefined,
    })
    posts.value = res.items
    total.value = res.total
    page.value = 1
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function loadMore() {
  if (loadingMore.value || !hasMore()) return
  loadingMore.value = true
  try {
    const res = await api.posts({
      page: page.value + 1,
      pageSize: PAGE_SIZE,
      tag: activeTag.value || undefined,
    })
    posts.value = [...posts.value, ...res.items]
    total.value = res.total
    page.value += 1
  } catch (err) {
    error.value = err.message
  } finally {
    loadingMore.value = false
  }
}

function selectTag(name) {
  activeTag.value = name
}

watch(activeTag, () => {
  loadFirstPage()
})

// 支持从其他页面带 ?tag= 跳转进来，以及在页面内切换查询参数
watch(
  () => route.query.tag,
  (next) => {
    const tag = next ? String(next) : ''
    if (tag !== activeTag.value) {
      activeTag.value = tag
    }
  },
)

onMounted(() => {
  const tag = tagFromQuery()
  if (tag === activeTag.value) {
    loadFirstPage()
  } else {
    activeTag.value = tag // 由 watch(activeTag) 触发加载，避免重复请求
  }
  fetchTags()
})
</script>

<template>
  <section class="articles container">
    <header class="page-head">
      <p class="eyebrow reveal">Articles</p>
      <h1 class="page-title reveal" style="--reveal-delay: 90ms">文章</h1>
      <p class="page-sub reveal" style="--reveal-delay: 170ms">
        共 <span class="num">{{ total }}</span> 篇，关于后端、RAG 与知识管理的记录。
      </p>
    </header>

    <!-- 标签筛选 -->
    <div v-if="tags.length" class="tag-row reveal" style="--reveal-delay: 240ms">
      <button
        class="tag-chip"
        :class="{ active: activeTag === '' }"
        type="button"
        @click="selectTag('')"
      >
        全部
      </button>
      <button
        v-for="tag in tags"
        :key="tag.id"
        class="tag-chip"
        :class="{ active: activeTag === tag.name }"
        type="button"
        @click="selectTag(tag.name)"
      >
        {{ tag.name }}
        <span class="tag-count">{{ tag.post_count }}</span>
      </button>
    </div>

    <!-- 列表 -->
    <p v-if="loading" class="notice">正在加载文章…</p>
    <p v-else-if="error" class="notice notice-error">
      加载失败：{{ error }}（请确认后端服务已启动）
    </p>
    <template v-else-if="posts.length">
      <div class="post-list">
        <PostCard
          v-for="(post, i) in posts"
          :key="post.id"
          :post="post"
          :index="i"
          v-reveal="(i % PAGE_SIZE) * 90"
        />
      </div>

      <div class="more-row">
        <button v-if="hasMore()" class="btn btn-ghost" type="button" :disabled="loadingMore" @click="loadMore">
          {{ loadingMore ? '加载中…' : '加载更多' }}
        </button>
        <p v-else class="more-end">— 已经到底了 —</p>
      </div>
    </template>
    <p v-else class="notice">该标签下暂无文章。</p>
  </section>
</template>

<style scoped>
.articles {
  padding-top: calc(var(--nav-h) + 84px);
  min-height: 70vh;
}

.page-head {
  margin-bottom: 40px;
}

.page-title {
  font-family: var(--font-serif);
  font-weight: 900;
  font-size: clamp(2.2rem, 5vw, 3.2rem);
  margin-top: 18px;
}

.page-sub {
  margin-top: 14px;
  color: var(--muted);
  font-size: 0.95rem;
}

.page-sub .num {
  font-family: var(--font-mono);
  color: var(--orange-hi);
}

/* 标签筛选 */
.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 36px;
}

.tag-chip {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 7px 16px;
  border-radius: 999px;
  border: 1px solid var(--line-strong);
  background: transparent;
  color: var(--muted);
  font-size: 0.85rem;
  transition: all 0.28s ease;
}

.tag-chip:hover {
  border-color: rgba(255, 122, 26, 0.5);
  color: var(--text);
  transform: translateY(-1px);
}

.tag-chip.active {
  background: var(--grad);
  border-color: transparent;
  color: #1c0d02;
  font-weight: 700;
  box-shadow: 0 8px 22px -10px rgba(255, 122, 26, 0.6);
}

.tag-count {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  opacity: 0.75;
}

.post-list {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.more-row {
  margin-top: 42px;
  display: flex;
  justify-content: center;
}

.more-end {
  font-family: var(--font-mono);
  font-size: 0.76rem;
  letter-spacing: 0.2em;
  color: var(--faint);
}

.btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  transform: none;
}
</style>
