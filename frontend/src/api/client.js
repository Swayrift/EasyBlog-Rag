/**
 * 后端 API 客户端。
 * 开发环境经 Vite 代理（/api -> http://127.0.0.1:8000），
 * 生产环境可由 Nginx 反代同路径，无需修改。
 */

const BASE = '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })
  if (!res.ok) {
    let detail = `请求失败（HTTP ${res.status}）`
    try {
      const body = await res.json()
      if (body && body.detail) {
        detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
      }
    } catch {
      /* 非 JSON 错误体，忽略 */
    }
    throw new Error(detail)
  }
  return res.json()
}

async function readErrorResponse(res) {
  let detail = `请求失败（HTTP ${res.status}）`
  try {
    const body = await res.json()
    if (body && body.detail) {
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    }
  } catch {
    /* 非 JSON 错误体，忽略 */
  }
  return detail
}

function parseSseEvent(block) {
  const data = block
    .split(/\r?\n/)
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.slice(5).trimStart())
    .join('\n')
  if (!data) return null
  return JSON.parse(data)
}

async function chatStream(messages, onEvent) {
  const res = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    },
    body: JSON.stringify({ messages }),
  })
  if (!res.ok) {
    throw new Error(await readErrorResponse(res))
  }
  if (!res.body) {
    throw new Error('浏览器不支持读取问答流')
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  const consume = async (flush = false) => {
    const blocks = buffer.split(/\r?\n\r?\n/)
    buffer = blocks.pop() || ''
    for (const block of blocks) {
      const event = parseSseEvent(block)
      if (event) await onEvent(event)
    }
    if (flush && buffer.trim()) {
      const event = parseSseEvent(buffer)
      if (event) await onEvent(event)
      buffer = ''
    }
  }

  while (true) {
    const { done, value } = await reader.read()
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done })
    await consume(done)
    if (done) break
  }
}

export const api = {
  health: () => request('/health'),

  posts: (params = {}) => {
    const qs = new URLSearchParams()
    if (params.page) qs.set('page', String(params.page))
    if (params.pageSize) qs.set('page_size', String(params.pageSize))
    if (params.tag) qs.set('tag', params.tag)
    const suffix = qs.toString() ? `?${qs.toString()}` : ''
    return request(`/posts${suffix}`)
  },

  post: (slug) => request(`/posts/${encodeURIComponent(slug)}`),

  /** 按数据库 id 查文章（问答引用来源跳转用），返回 slug 等信息 */
  postById: (id) => request(`/posts/id/${id}`),

  tags: () => request('/tags'),

  about: () => request('/about'),

  chat: (messages, onEvent = () => {}) => chatStream(messages, onEvent),
  chatStream,
}
