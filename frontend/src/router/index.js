import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
      meta: { title: '首页' },
    },
    {
      path: '/articles',
      name: 'articles',
      component: () => import('@/views/ArticlesView.vue'),
      meta: { title: '文章' },
    },
    {
      path: '/posts/:slug',
      name: 'post',
      component: () => import('@/views/PostDetailView.vue'),
      // bare：不显示顶部导航栏与页脚，仅有返回按钮
      meta: { title: '文章详情', bare: true },
    },
    {
      path: '/chat',
      name: 'chat',
      component: () => import('@/views/ChatView.vue'),
      meta: { title: '知识库问答', hideFooter: true },
    },
    {
      path: '/about',
      name: 'about',
      component: () => import('@/views/AboutView.vue'),
      meta: { title: '关于我' },
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
  scrollBehavior() {
    return { top: 0 }
  },
})

router.afterEach((to) => {
  document.title = to.meta.title
    ? `${to.meta.title} · SwayRift 的博客`
    : 'SwayRift 的博客'
})

export default router
