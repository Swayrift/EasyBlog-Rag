---
title: 如何在你的页面中实现流式输出
slug: stream-output
summary: 基于 FastAPI 与 Vue 3 实现 SSE（Server-Sent Events）流式打字机输出，从最小可运行示例讲到 RAG 问答的多阶段事件推流，并整理了几个实际会踩的坑。
tags: [Vue3, FastAPI, SSE, RAG]
status: published
created_at: 2026-05-15 12:20:00
---

## 简单介绍

在页面中实现流式输出，最常用的技术是 SSE（Server-Sent Events）。它是基于 HTTP 的轻量级单向流式传输协议：服务端可以持续往同一个连接里写数据，客户端边收边渲染，很适合去做一个流式输出。

相比 WebSocket，它不需要另起一套协议和握手，也不是二进制帧，就是一段普通的 HTTP 响应体；相比轮询，它没有空转请求。代价是方向单一——只能服务端推、客户端收。打字机效果、进度提示、日志滚动这类场景本来就不需要反向通道，所以够用。

下面以 FastAPI 作后端、Vue 3 作前端为例，先看最基础的实现，再看如何用事件类型做多阶段推流。

## 基础代码实现

对于最基础的流式输出，关键部分代码如下：

```python
# 后端实现 (FastAPI)
import asyncio
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()


def format_sse(data: str, event: str = "") -> str:
    """按 SSE 规范拼一个消息块：字段行 + 一个空行结束"""
    # 一行的数据写成 "data: xxx"；数据里如果有换行，必须拆成多个 data: 行，
    # 客户端解析时再用 \n 把它们拼回一条数据
    body = "".join(f"data: {line}\n" for line in str(data).split("\n"))
    head = f"event: {event}\n" if event else ""
    return f"{head}{body}\n"


async def text_stream_generator():
    """模拟流式生成数据的异步生成器"""
    demo_text = "你好！这是使用 FastAPI 和 Vue 3 实现的 SSE 流式打字机效果示例。响应数据正在实时推送中..."

    # 逐字/逐词模拟大模型流式输出
    for char in demo_text:
        yield format_sse(char)
        await asyncio.sleep(0.08)  # 模拟延时


@app.get("/api/stream")
async def get_stream():
    """SSE 流式接口"""
    return StreamingResponse(
        text_stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 防止 Nginx 缓存流数据
        },
    )
```

```javascript
// 前端实现 (Vue 3)
import { ref } from 'vue'

const textBuffer = ref('')
const isStreaming = ref(false)

const startStreaming = async () => {
  textBuffer.value = ''
  isStreaming.value = true

  try {
    const response = await fetch('http://127.0.0.1:8000/api/stream', {
      method: 'GET',
      headers: {
        Accept: 'text/event-stream'
      }
    })

    if (!response.ok || !response.body) {
      throw new Error('网络响应异常或无法建立流式连接')
    }

    // 获取读取器与 UTF-8 解码器
    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let pending = ''  // 上一轮没读完整的尾巴

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      // 解码数据块（设置 stream: true 以防多字节字符在块边界中断裂）
      pending += decoder.decode(value, { stream: true })

      // 消息块之间用空行分隔
      const blocks = pending.split('\n\n')
      pending = blocks.pop() || ''  // 最后一段可能不完整，留到下一轮拼

      for (const block of blocks) {
        // 一个消息块可以有多个 data: 行，用 \n 连接成一条数据
        const dataLines = block.split('\n')
          .filter((line) => line.startsWith('data:'))
          .map((line) => line.slice(5).replace(/^ /, ''))  // 只吃掉一个空格

        if (dataLines.length) {
          textBuffer.value += dataLines.join('\n')
        }
      }
    }
  } catch (error) {
    console.error('流处理异常:', error)
  } finally {
    isStreaming.value = false
  }
}
```

这段前端代码有两个地方和"随便写写"的版本不一样，值得说明一下。

一是 `pending`。一次 `reader.read()` 拿到的数据块，和一条完整的 SSE 消息没有对应关系：可能只有半条，也可能一次读回三条。所以不能读完就切、切完就丢，必须把最后一个不完整的片段留到下一轮。凡是漏了这一步的实现，都会在数据量大、推送密集的时候随机丢字符——而且因为字符少一个不容易察觉，很容易被当成"模型偶尔说错话"。

二是解析 `data:` 时只去掉一个空格。规范里的规则是"冒号后如果紧跟着一个空格，去掉这一个"，所以 `data:  hello`（两个空格）的值是 ` hello`，用 `/^data:\s*/` 会多吃掉一个空格，缩进和代码块就会错位。

## SSE 的标准字段定义

规范中定义了 4 个合法的字段名，区分大小写，分别是：`data`、`event`、`id`、`retry`。除此之外，以 `:` 开头的行是注释，不算字段。

这是一个完整的、包含各种发送方式的 SSE 数据流：

```
: 注释内容

retry: 3000

id: 1
event: start
data: 开始生成内容...

id: 2
data: 这是第一段数据
data: 这是紧接着的下一行

id: 3
event: progress
data: {"progress": 80, "step": "analyzing"}

id: 4
event: end
data: [DONE]
```

在这段数据流中：

- `: ` 后的是注释内容，客户端会直接忽略。它最常见的用途是当心跳——长时间没有数据时定期发一行注释，防止中间层超时断连。
- `retry: ` 表示重连间隔时间（毫秒）。连接意外断开后，客户端会等这个间隔再自动重连。
- `id: ` 是事件 ID。断线重连时浏览器会在 `Last-Event-ID` 请求头里带上最后一个 ID，服务端可以据此续传。
- 一个消息块可以包含多个 `data: `，客户端解析时会用 `\n` 把它们拼成一条数据——所以数据里的换行只能这么表达，不能直接塞裸换行。
- `event: ` 表示当前正在发生的事件（文章后面会做演示）。不写的时候默认事件类型是 `message`。
- **空行才是分隔符。** 只有读到空行，客户端才认为这条消息发送完毕并交给业务代码。少一个空行，数据就一直卡在缓冲里。
- `data: [DONE]` 用来表示这段数据流结束——需要说明的是，这是 OpenAI 那类流式接口的约定，不是 SSE 规范的一部分。规范里并没有"结束事件"这个概念：判断结束要么靠服务端关闭连接，要么由应用层自己约定一个字段（比如后面用到的 `event: done`）或哨兵值。

## 进阶用法示例：RAG 多阶段状态推送与文本流式输出

以本站 RAG 问答流式输出为例，在用户发送提问到后端服务器后，服务器会经历：读取 FAQ 缓存、Query 改写、检索知识库、重排检索结果、生成回答五个阶段。如果不使用 SSE 流式输出，那么用户需要等待五个阶段的完整流程跑完才能看到结果，服务器对于用户来说是一个黑盒，他不知道服务器内部到底有没有在处理他的问题，只能干着急，因此流式输出是很有必要的。

对 SSE 深入了解后可以发现，它是允许传输事件的，这样就可以实时告知用户，服务器目前正在进行哪个阶段。为了实现"实时状态更新（如：检索中...） + 文本逐字推流"的效果，我们需要充分利用 SSE 的 `event:` 字段来定义不同的事件类型（例如：`status` 用于更新进度，`message` 用于输出回答文本，`done` 表示完成）。

另外还有一件容易被忽略的事：**用户在生成到一半时关掉页面，后端不该继续算下去。** 所以下面在接口外面包了一层，负责在客户端断开时把生成器关掉。关键部分代码如下：

```python
# 后端实现 (FastAPI)
import asyncio
import json
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

app = FastAPI()


def format_sse(event: str, data: dict | str) -> str:
    """格式化 SSE 消息块：event 行可选，data 里含换行时自动拆成多行"""
    payload = json.dumps(data, ensure_ascii=False) if isinstance(data, dict) else str(data)
    body = "".join(f"data: {line}\n" for line in payload.split("\n"))
    return f"event: {event}\n{body}\n"


async def rag_pipeline_generator(query: str):
    """模拟 RAG 流程的多阶段 SSE 推送"""

    # 阶段 1：读取 FAQ 缓存
    yield format_sse("status", {"step": 1, "label": "正在匹配 FAQ 缓存..."})
    await asyncio.sleep(0.5)

    # 阶段 2：Query 改写
    yield format_sse("status", {"step": 2, "label": "正在进行 Query 改写..."})
    await asyncio.sleep(0.6)

    # 阶段 3 & 4：检索知识库与重排
    yield format_sse("status", {"step": 3, "label": "正在检索知识库并重排结果..."})
    await asyncio.sleep(0.8)

    # 阶段 5：开始生成回答（切换事件类型为 message）
    yield format_sse("status", {"step": 4, "label": "生成回答中..."})

    answer_text = f"针对您的提问『{query}』，结合知识库检索到的信息，解答如下：SSE 协议天然支持事件分类..."
    for char in answer_text:
        # 实际接大模型时，这里直接 yield 模型吐出来的 token 段即可，不必逐字拆
        yield format_sse("message", {"content": char})
        await asyncio.sleep(0.05)

    # 流程结束
    yield format_sse("done", {"status": "completed"})


@app.get("/api/rag/stream")
async def rag_stream(query: str, request: Request):
    async def event_source():
        generator = rag_pipeline_generator(query)
        try:
            async for chunk in generator:
                if await request.is_disconnected():
                    break  # 客户端已经走了，停止推流
                yield chunk
        finally:
            await generator.aclose()  # 及时收尾，别让检索/生成线程继续空跑

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

把断开检测放在这一层，好处是生成器本身不用到处插判断，内部逻辑保持干净；用户点开再关掉页面几秒钟，后端也不会白烧一遍检索和生成。

```javascript
// 前端实现 (Vue 3)
import { ref } from 'vue'

const currentStatus = ref('')   // 存储当前阶段提示（如：正在检索知识库...）
const answerBuffer = ref('')    // 存储生成的回答文本
const isProcessing = ref(false)
let controller = null

const stopRagStream = () => {
  controller?.abort()           // 主动断开连接，后端会通过 is_disconnected() 感知到
}

const startRagStream = async (userQuery) => {
  currentStatus.value = '准备建立连接...'
  answerBuffer.value = ''
  isProcessing.value = true
  controller = new AbortController()

  try {
    const response = await fetch(`/api/rag/stream?query=${encodeURIComponent(userQuery)}`, {
      signal: controller.signal
    })
    if (!response.ok || !response.body) throw new Error('流连接失败')

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let pendingChunk = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      pendingChunk += decoder.decode(value, { stream: true })

      // 按标准 SSE 双换行切分事件块
      const blocks = pendingChunk.split('\n\n')
      // 最后一个可能不完整，留到下一轮处理
      pendingChunk = blocks.pop() || ''

      for (const block of blocks) {
        if (!block.trim()) continue

        let eventType = 'message' // 默认事件类型
        const dataLines = []

        // 解析块内的每一行
        const lines = block.split('\n')
        for (const line of lines) {
          if (line.startsWith('event:')) {
            eventType = line.slice(6).replace(/^ /, '').trim()
          } else if (line.startsWith('data:')) {
            dataLines.push(line.slice(5).replace(/^ /, ''))
          }
        }

        const dataContent = dataLines.join('\n')

        // 尝试解析 JSON 数据
        let parsedData = dataContent
        try { parsedData = JSON.parse(dataContent) } catch (e) {}

        // 根据事件类型做响应式更新
        if (eventType === 'status') {
          currentStatus.value = parsedData.label
        } else if (eventType === 'message') {
          answerBuffer.value += parsedData.content
        } else if (eventType === 'done') {
          currentStatus.value = '生成完成'
        } else if (eventType === 'error') {
          currentStatus.value = `出错了：${parsedData.message}`
        }
      }
    }
  } catch (err) {
    if (err.name === 'AbortError') {
      currentStatus.value = '已停止生成'
    } else {
      console.error('RAG 流解析异常:', err)
      currentStatus.value = '出错了，请重试'
    }
  } finally {
    isProcessing.value = false
    controller = null
  }
}
```

前端这边有三处是实际用起来之后补的，一并说明：数据行改成累积再 `join('\n')`（原来只保留最后一行，JSON 里出现换行就会被截断）；接了 `AbortController` 让用户可以中途停下；以及单独处理 `error` 事件与 `AbortError`——把"主动停止"和"真的出错"混在同一个 catch 里，体验会很差。

## 几个容易踩的坑

前面代码里已经提到的两点（分块不等于消息、`data:` 后只吃一个空格）这里不重复，剩下的都是实际部署时才会遇到的。

**`\r` 和 `\r\n` 的换行。** SSE 规范允许消息块之间用 `\n\n`、`\r\n\r\n` 或 `\r\r` 分隔，而本文的实现是按 `\n\n` 切的。如果中间件或某些框架把换行统一成了 `\r\n`，切块就会失配，表现为消息一直不出。解决办法要么是在拼接前统一换行符，要么直接用浏览器原生的 `EventSource`，它能正确处理这三种换行。

**数据里不能有裸换行或裸 `\r`。** 裸换行会被当成字段行结束，裸 `\r` 会被当成消息分隔符，直接破坏整条流。所以结构化数据一律走 `json.dumps` / `JSON.stringify`，标量文本要么走多行 `data:`，要么把 `\r` 处理掉。

**中间层会缓冲。** Nginx 需要写 `X-Accel-Buffering: no`，否则数据攒够一个 buffer 才吐出来，打字机效果会变成"一顿一顿地整段出现"。另外不少网关和负载均衡对空闲连接有 60 秒左右的超时，需要定期发一行 `: ping` 当心跳。

**别把业务错误塞进流里当成功返回。** 响应头在流开始的那一刻就已经发出去了，之后无论发生什么，HTTP 状态码都改不了。所以"查询参数不合法"这类错误应该在开始推流之前就返回正常的错误状态码；一旦开始推流，就只能靠约定一个 `event: error` 把错误告诉前端。本文的示例就是这么分的。

**为什么用 fetch 而不是 `EventSource`。** `EventSource` 只支持 GET，不能带请求体、也加不了自定义请求头（比如 `Authorization`）。本文的 RAG 场景里，问题文本本身就该走请求体或至少是 POST，鉴权也需要请求头，所以用了 `fetch` + `ReadableStream` 自己解析。代价就是要自己处理分块和重连；如果想要浏览器自动重连那套现成能力，用 `EventSource` 更省事。

**自动重连可能是个陷阱。** `EventSource` 在连接断开后默认会按 `retry` 反复重连，这对推送类场景是好事，对"一次问答"却是坏事——用户会看到回答从头开始生成两遍。如果用了 `EventSource`，记得是在收到结束事件后主动 `close()`，或者由服务端在结束时返回 `204` 让浏览器停止重连。

**连接数是有限资源。** HTTP/1.1 下浏览器对同一域名只允许 6 个并发连接，每开一条 SSE 就长期占掉一个，同时打开多个问答页签很容易把其他请求堵住。上 HTTP/2 可以绕开这个限制，或者干脆在切页签时主动断开。
