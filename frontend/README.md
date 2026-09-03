# 博客前端

Vue 3 + Vite + Vue Router 的个人博客前端，黑色 × 橙色的编辑风格主题，
配套后端见 `../backend`（FastAPI + SQLite + FAISS）。

## 页面结构

- `/` 首页：Hero、个人简介、最新文章、标签入口、知识库问答引导
- `/articles` 文章列表：标签筛选 + 分页加载（支持 ?tag= 深链）
- `/posts/:slug` 文章详情：仅返回按钮，Markdown 渲染
- `/chat` 知识库问答：RAG 检索，回答附带引用来源
- `/about` 关于我：技术栈、联系方式

顶部导航栏出现在除文章详情外的所有页面，含「主页」链接与品牌 Logo 两种回首页入口；文章详情页仅有返回按钮。

## 目录约定

```
src/
  api/client.js        后端接口封装（统一 /api 前缀）
  assets/main.css      全局主题（CSS 变量、入场动效、按钮等）
  components/          TheNavbar / TheFooter / PostCard / MarkdownView
  directives/reveal.js v-reveal 指令：滚动进入视口时的入场动画
  router/index.js      路由与页面标题
  views/               五个页面视图
```

## 开发

```sh
npm install
npm run dev        # http://localhost:5173，/api 已代理到 http://127.0.0.1:8000
```

开发前请先启动后端（见 `../backend/README.md`），否则页面会显示加载失败提示。

## 构建

```sh
npm run build      # 产物输出到 dist/，可由 Nginx 托管并反代 /api 到后端
```
