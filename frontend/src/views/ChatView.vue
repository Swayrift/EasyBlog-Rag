<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { api } from '@/api/client'
import MarkdownView from '@/components/MarkdownView.vue'
import { useChatStore } from '@/stores/chat'

const chatStore = useChatStore()
const { messages } = storeToRefs(chatStore)
const input = ref('')
const busy = computed(() => chatStore.hasPendingMessage)
const health = ref(null)
const threadEl = ref(null)
const inputEl = ref(null)

// post 类型引用来源的 id -> slug 映射（用于跳转文章详情）
const slugs = ref({})
const slugCache = new Map()

const suggestions = [
  '这个博客用了哪些技术栈？',
  'RAG 知识库问答的流程是怎样的？',
  '检索效果可以怎么调优？',
]

const statusText = computed(() => {
  if (!health.value) return '检测中…'
  return health.value.vector_store_ok ? '知识库在线' : '知识库离线'
})

function scrollToBottom() {
  nextTick(() => {
    if (threadEl.value) {
      threadEl.value.scrollTop = threadEl.value.scrollHeight
    }
  })
}

async function resolveSlugs(sources) {
  for (const source of sources) {
    if (source.source_type !== 'post') continue
    const id = source.source_id
    if (slugCache.has(id)) {
      const cached = slugCache.get(id)
      if (cached) slugs.value = { ...slugs.value, [id]: cached }
      continue
    }
    api
      .postById(id)
      .then((post) => {
        slugCache.set(id, post.slug)
        slugs.value = { ...slugs.value, [id]: post.slug }
      })
      .catch(() => slugCache.set(id, null))
  }
}

function resolveStoredSlugs() {
  messages.value
    .filter((message) => message.role === 'assistant' && message.sources?.length)
    .forEach((message) => resolveSlugs(message.sources))
}

async function send(text) {
  const content = (text ?? input.value).trim()
  if (!content || busy.value) return

  input.value = ''
  resetInputHeight()
  chatStore.addUserMessage(content)
  const pendingIndex = chatStore.addAssistantMessage()
  scrollToBottom()

  try {
    const history = messages.value
      .filter((m) => !m.loading && !m.error && m.content)
      .slice(-20)
      .map((m) => ({ role: m.role, content: m.content }))
    const res = await api.chat(history)
    chatStore.completeAssistantMessage(pendingIndex, res.answer, res.sources || [])
    resolveSlugs(res.sources || [])
  } catch (err) {
    chatStore.failAssistantMessage(pendingIndex, err.message)
  } finally {
    chatStore.finishAssistantMessage(pendingIndex)
    scrollToBottom()
  }
}

function toggleSource(messageIndex, sourceIndex) {
  chatStore.toggleSource(messageIndex, sourceIndex)
}

function onKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault()
    send()
  }
}

function resetInputHeight() {
  nextTick(() => {
    if (!inputEl.value) return
    inputEl.value.style.height = 'auto'
  })
}

function autoGrow(event) {
  const el = event.target
  el.style.height = 'auto'
  el.style.height = `${Math.min(el.scrollHeight, 160)}px`
}

function scorePercent(score) {
  const clamped = Math.max(0, Math.min(1, Number(score) || 0))
  return `${Math.round(clamped * 100)}%`
}

onMounted(async () => {
  try {
    health.value = await api.health()
  } catch {
    health.value = null
  }
  resolveStoredSlugs()
  inputEl.value?.focus()
})
</script>

<template>
  <div class="chat">
    <!-- 顶部标题与状态 -->
    <header class="chat-head container">
      <div class="chat-head-text">
        <p class="eyebrow">RAG Knowledge QA</p>
        <h1 class="chat-title">知识库问答</h1>
      </div>
      <span class="chat-status">
        <span
          class="dot"
          :class="health && health.vector_store_ok ? 'dot-on' : 'dot-off'"
        ></span>
        {{ statusText }}
      </span>
    </header>

    <div v-if="health && !health.vector_store_ok" class="container">
      <p class="chat-warn">
        向量库当前不可用，问答无法检索知识库内容。请确认后端已安装 milvus-lite 并正常启动。
      </p>
    </div>

    <!-- 对话区 -->
    <div ref="threadEl" class="chat-thread">
      <div class="container chat-thread-inner">
        <!-- 空状态 -->
        <div v-if="!messages.length" class="chat-empty">
          <p class="chat-empty-title">向我的文章与文档提问</p>
          <p class="chat-empty-sub">
            问题会经过查询改写、向量检索与重排序，回答附带引用来源。
          </p>
          <div class="chat-suggestions">
            <button
              v-for="s in suggestions"
              :key="s"
              class="suggestion"
              type="button"
              @click="send(s)"
            >
              {{ s }}
            </button>
          </div>
        </div>

        <!-- 消息流 -->
        <template v-else>
          <div
            v-for="(message, i) in messages"
            :key="i"
            class="msg-row"
            :class="message.role"
          >
            <!-- 用户消息 -->
            <div v-if="message.role === 'user'" class="msg-user">{{ message.content }}</div>

            <!-- 助手消息 -->
            <div v-else class="msg-bot">
              <div v-if="message.loading" class="typing" aria-label="正在思考">
                <span></span><span></span><span></span>
              </div>
              <template v-else>
                <p v-if="message.error" class="msg-error">出错了：{{ message.error }}</p>
                <template v-else>
                  <MarkdownView :source="message.content" />

                  <div v-if="message.sources && message.sources.length" class="sources">
                    <p class="sources-title">引用来源 · {{ message.sources.length }}</p>
                    <div
                      v-for="(source, si) in message.sources"
                      :key="si"
                      class="source-card"
                      :class="{ expanded: message.expanded[si] }"
                      role="button"
                      tabindex="0"
                      :aria-expanded="!!message.expanded[si]"
                      @click="toggleSource(i, si)"
                      @keydown.enter.prevent="toggleSource(i, si)"
                      @keydown.space.prevent="toggleSource(i, si)"
                    >
                      <div class="source-head">
                        <span class="source-type">
                          {{ source.source_type === 'post' ? '文章' : '文档' }}
                        </span>
                        <span class="source-title">{{ source.title }}</span>
                        <span class="source-score">
                          <span class="source-score-bar">
                            <span
                              class="source-score-fill"
                              :style="{ width: scorePercent(source.score) }"
                            ></span>
                          </span>
                          {{ scorePercent(source.score) }}
                        </span>
                        <span class="source-toggle" aria-hidden="true">
                          <svg
                            class="source-chevron"
                            :class="{ open: message.expanded[si] }"
                            viewBox="0 0 16 16"
                            width="12"
                            height="12"
                          >
                            <path
                              d="M4 6l4 4 4-4"
                              fill="none"
                              stroke="currentColor"
                              stroke-width="2"
                              stroke-linecap="round"
                              stroke-linejoin="round"
                            />
                          </svg>
                          {{ message.expanded[si] ? '收起' : '展开' }}
                        </span>
                      </div>
                      <p v-if="message.expanded[si]" class="source-chunk">
                        {{ source.chunk }}
                      </p>
                      <RouterLink
                        v-if="source.source_type === 'post' && slugs[source.source_id]"
                        :to="`/posts/${slugs[source.source_id]}`"
                        class="source-link"
                        @click.stop
                      >
                        查看原文 →
                      </RouterLink>
                    </div>
                  </div>
                </template>
              </template>
            </div>
          </div>
        </template>
      </div>
    </div>

    <!-- 输入区 -->
    <div class="chat-input-bar">
      <div class="container chat-input-inner">
        <textarea
          ref="inputEl"
          v-model="input"
          class="chat-input"
          rows="1"
          placeholder="输入你的问题"
          @keydown="onKeydown"
          @input="autoGrow"
        ></textarea>
        <button
          class="send-btn"
          type="button"
          :disabled="busy || !input.trim()"
          aria-label="发送"
          @click="send()"
        >
          <span class="send-icon" aria-hidden="true">↑</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat {
  display: flex;
  flex-direction: column;
  height: 100dvh;
  padding-top: var(--nav-h);
}

/* ---------- 头部 ---------- */
.chat-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  padding-top: 26px;
  padding-bottom: 18px;
  border-bottom: 1px solid var(--line);
}

.chat-title {
  font-family: var(--font-serif);
  font-weight: 900;
  font-size: 1.6rem;
  margin-top: 8px;
}

.chat-status {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  font-family: var(--font-mono);
  font-size: 0.74rem;
  letter-spacing: 0.12em;
  color: var(--muted);
  padding-bottom: 6px;
}

.chat-warn {
  margin-top: 12px;
  font-size: 0.82rem;
  color: #ffb08a;
  background: rgba(255, 122, 26, 0.08);
  border: 1px solid rgba(255, 122, 26, 0.25);
  border-radius: 10px;
  padding: 10px 14px;
}

/* ---------- 对话区 ---------- */
.chat-thread {
  flex: 1;
  overflow-y: auto;
  scroll-behavior: smooth;
}

.chat-thread-inner {
  padding-top: 36px;
  padding-bottom: 36px;
  display: flex;
  flex-direction: column;
  gap: 26px;
  max-width: 860px;
}

/* 空状态 */
.chat-empty {
  margin: auto;
  padding-top: 8vh;
  text-align: center;
}

.chat-empty-title {
  font-family: var(--font-serif);
  font-weight: 900;
  font-size: 1.5rem;
}

.chat-empty-sub {
  margin-top: 10px;
  color: var(--muted);
  font-size: 0.9rem;
}

.chat-suggestions {
  margin-top: 30px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.suggestion {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--line-strong);
  color: var(--muted);
  border-radius: 999px;
  padding: 9px 22px;
  font-size: 0.88rem;
  transition: all 0.28s ease;
}

.suggestion:hover {
  border-color: rgba(255, 122, 26, 0.6);
  color: var(--orange-hi);
  background: rgba(255, 122, 26, 0.07);
  transform: translateY(-2px);
}

/* 消息 */
.msg-row {
  display: flex;
}

.msg-row.user {
  justify-content: flex-end;
}

.msg-user {
  max-width: 76%;
  background: var(--grad);
  color: #1c0d02;
  font-weight: 500;
  padding: 12px 18px;
  border-radius: 18px 18px 5px 18px;
  box-shadow: 0 12px 28px -14px rgba(255, 122, 26, 0.55);
  white-space: pre-wrap;
  word-break: break-word;
  animation: msg-in 0.4s cubic-bezier(0.22, 0.61, 0.36, 1);
}

.msg-bot {
  max-width: 88%;
  background: var(--bg-soft);
  border: 1px solid var(--line);
  border-radius: 5px 18px 18px 18px;
  padding: 18px 22px;
  animation: msg-in 0.45s cubic-bezier(0.22, 0.61, 0.36, 1);
}

@keyframes msg-in {
  from {
    opacity: 0;
    transform: translateY(14px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

.msg-error {
  color: #ff9a80;
  font-size: 0.9rem;
}

/* 正在思考 */
.typing {
  display: inline-flex;
  gap: 6px;
  padding: 4px 2px;
}

.typing span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--orange);
  animation: typing-bounce 1.2s ease-in-out infinite;
}

.typing span:nth-child(2) {
  animation-delay: 0.15s;
}

.typing span:nth-child(3) {
  animation-delay: 0.3s;
}

@keyframes typing-bounce {
  0%,
  60%,
  100% {
    transform: translateY(0);
    opacity: 0.4;
  }
  30% {
    transform: translateY(-6px);
    opacity: 1;
  }
}

/* 引用来源 */
.sources {
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px dashed var(--line-strong);
}

.sources-title {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  letter-spacing: 0.2em;
  color: var(--faint);
  margin-bottom: 12px;
}

.source-card {
  border: 1px solid var(--line);
  border-radius: 12px;
  background: rgba(255, 122, 26, 0.04);
  padding: 12px 16px;
  cursor: pointer;
  transition: border-color 0.25s ease;
  user-select: none;
}

.source-card + .source-card {
  margin-top: 10px;
}

.source-card:hover {
  border-color: rgba(255, 122, 26, 0.4);
}

.source-card.expanded {
  border-color: rgba(255, 122, 26, 0.55);
  background: rgba(255, 122, 26, 0.07);
}

.source-head {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.source-type {
  font-family: var(--font-mono);
  font-size: 0.68rem;
  letter-spacing: 0.1em;
  padding: 2px 9px;
  border-radius: 999px;
  background: rgba(255, 122, 26, 0.14);
  color: var(--orange-hi);
}

.source-title {
  font-weight: 600;
  font-size: 0.9rem;
}

.source-score {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--faint);
}

.source-score-bar {
  width: 54px;
  height: 4px;
  border-radius: 4px;
  background: rgba(255, 235, 214, 0.08);
  overflow: hidden;
}

.source-score-fill {
  display: block;
  height: 100%;
  background: var(--grad);
  border-radius: 4px;
}

.source-toggle {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-family: var(--font-mono);
  font-size: 0.68rem;
  letter-spacing: 0.08em;
  color: var(--orange-hi);
  white-space: nowrap;
}

.source-chevron {
  transition: transform 0.25s ease;
}

.source-chevron.open {
  transform: rotate(180deg);
}

.source-chunk {
  margin-top: 8px;
  font-size: 0.82rem;
  color: var(--muted);
  line-height: 1.75;
  white-space: pre-wrap;
  word-break: break-word;
  animation: chunk-in 0.25s ease;
}

@keyframes chunk-in {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

.source-link {
  display: inline-block;
  margin-top: 8px;
  font-size: 0.8rem;
  color: var(--orange-hi);
  transition: color 0.25s ease, transform 0.25s ease;
}

.source-link:hover {
  color: #ffc46b;
  transform: translateX(3px);
}

/* ---------- 输入区 ---------- */
.chat-input-bar {
  border-top: 1px solid var(--line);
  background: rgba(10, 8, 7, 0.82);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  padding: 16px 0 20px;
}

.chat-input-inner {
  max-width: 860px;
  display: flex;
  align-items: flex-end;
  gap: 12px;
}

.chat-input {
  flex: 1;
  resize: none;
  background: var(--bg-soft);
  border: 1px solid var(--line-strong);
  border-radius: 14px;
  color: var(--text);
  font-family: inherit;
  font-size: 0.95rem;
  line-height: 1.6;
  padding: 12px 16px;
  max-height: 160px;
  transition: border-color 0.25s ease, box-shadow 0.25s ease;
}

.chat-input::placeholder {
  color: var(--faint);
}

.chat-input:focus {
  outline: none;
  border-color: rgba(255, 122, 26, 0.6);
  box-shadow: 0 0 0 3px rgba(255, 122, 26, 0.14);
}

.send-btn {
  flex: none;
  width: 46px;
  height: 46px;
  border-radius: 50%;
  border: none;
  background: var(--grad);
  color: #1c0d02;
  font-size: 1.2rem;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 10px 26px -10px rgba(255, 122, 26, 0.6);
  transition: transform 0.25s ease, box-shadow 0.25s ease, opacity 0.25s ease;
}

.send-btn:hover:not(:disabled) {
  transform: translateY(-2px) scale(1.04);
  box-shadow: 0 14px 32px -10px rgba(255, 122, 26, 0.75);
}

.send-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  box-shadow: none;
}

@media (max-width: 640px) {
  .msg-user {
    max-width: 88%;
  }
  .msg-bot {
    max-width: 100%;
  }
}
</style>
