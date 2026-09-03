---
title: 如何在你的页面中实现流式输出
slug: stream-output
summary: 本文详细介绍了如何基于 FastAPI 与 Vue 3 实现 SSE（Server-Sent Events）流式打字机输出，并以 RAG 问答的多阶段事件推流为例给出进阶落地代码。
tags: [Vue3, FastAPI, SSE, RAG]
status: published
created_at: 2026-05-15 12:20:00
---

## 简单介绍

在页面中实现流式输出主要是使用一个 SSE（Server-Sent Events）技术，它是基于 HTTP 的轻量级单向流式传输协议，很适合去做一个流式输出。

## 基础代码实现

对于最基础的流式输出，关键部分代码如下：
```python
# 后端实现 (FastAPI)
import asyncio
import json
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()

async def text_stream_generator():
    """模拟流式生成数据的异步生成器"""
    demo_text = "你好！这是使用 FastAPI 和 Vue 3 实现的 SSE 流式打字机效果示例。响应数据正在实时推送中..."
    
    # 逐字/逐词模拟大模型流式输出
    for char in demo_text:
        # SSE 规范格式：以 "data: " 开头，双换行 "\n\n" 结束
        yield f"data: {char}\n\n"
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
            "X-Accel-Buffering": "no"  # 防止 Nginx 缓存流数据
        }
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
        'Accept': 'text/event-stream'
      }
    })

    if (!response.ok || !response.body) {
      throw new Error('网络响应异常或无法建立流式连接')
    }

    // 获取读取器与 UTF-8 解码器
    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      // 解码数据块（设置 stream: true 以防多字节字符在块边界中断裂）
      const chunk = decoder.decode(value, { stream: true })
      
      // 按行解析 SSE 格式的数据包
      const lines = chunk.split('\n\n')
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const content = line.replace(/^data:\s*/, '')
          textBuffer.value += content
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

## SSE 的标准字段定义

规范中定义了4个合法字段名，区分大小写，分别是：`data、event、id、retry`以及`: Comment`注释。

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
在这段数据流中，`: `后的为注释内容，`retry: `表示重连间隔时间，一个消息块可以包含多个`data: `，消息块中可以包含`event: `表示当前正在发生的事件（文章后面会做演示），使用`data: [DONE]`表示这段数据流结束。

## 进阶用法示例：RAG 多阶段状态推送与文本流式输出

以本站 RAG 问答流式输出为例，在用户发送提问到后端服务器后，服务器会经历：读取 FAQ 缓存、Query 改写、检索知识库、重排检索结果、生成回答五个阶段，如果不使用 SSE 流式输出，那么用户需要等待五个阶段的完整流程跑完，才能看到结果，服务器对于用户来说是一个黑盒，他不知道服务器内部到底有没有在处理他的问题，只能干着急，因此流式输出是很有必要的。

对 SSE 深入了解后，可以发现它是允许传输事件的，这样就可以实时告知用户，服务器目前正在进行哪个阶段。为了实现“实时状态更新（如：检索中...） + 文本逐字推流”的效果，我们需要充分利用 SSE 的 `event:` 字段来定义不同的事件类型（例如：`status` 用于更新进度，`message` 用于输出回答文本，`done` 表示完成）。关键部分代码如下：
```python
# 后端实现 (FastAPI)
import asyncio
import json
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()

async def rag_pipeline_generator(query: str):
    """模拟 RAG 流程的多阶段 SSE 推送"""
    
    # 辅助函数：格式化 SSE 消息块
    def format_sse(event: str, data: dict | str) -> str:
        payload = json.dumps(data, ensure_ascii=False) if isinstance(data, dict) else str(data)
        return f"event: {event}\ndata: {payload}\n\n"

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
        yield format_sse("message", {"content": char})
        await asyncio.sleep(0.05)

    # 流程结束
    yield format_sse("done", {"status": "completed"})

@app.get("/api/rag/stream")
async def rag_stream(query: str):
    return StreamingResponse(
        rag_pipeline_generator(query),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
```

```javascript
// 前端实现 (Vue 3)
import { ref } from 'vue'

const currentStatus = ref('')   // 存储当前阶段提示（如：正在检索知识库...）
const answerBuffer = ref('')    // 存储生成的回答文本
const isProcessing = ref(false)

const startRagStream = async (userQuery) => {
  currentStatus.value = '准备建立连接...'
  answerBuffer.value = ''
  isProcessing.value = true

  try {
    const response = await fetch(`/api/rag/stream?query=${encodeURIComponent(userQuery)}`)
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
        let dataContent = ''

        // 解析块内的每一行
        const lines = block.split('\n')
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.replace(/^event:\s*/, '').trim()
          } else if (line.startsWith('data: ')) {
            dataContent = line.replace(/^data:\s*/, '').trim()
          }
        }

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
        }
      }
    }
  } catch (err) {
    console.error('RAG 流解析异常:', err)
  } finally {
    isProcessing.value = false
  }
}
```