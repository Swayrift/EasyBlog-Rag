<script setup>
import { RouterLink, useRoute } from 'vue-router'

const route = useRoute()

const links = [
  { name: '主页', to: '/' },
  { name: '文章', to: '/articles' },
  { name: '问答', to: '/chat' },
  { name: '关于', to: '/about' },
]

function isActive(to) {
  if (to === '/') {
    return route.path === '/'
  }
  return route.path === to || route.path.startsWith(`${to}/`)
}
</script>

<template>
  <header class="nav">
    <div class="container nav-inner">
      <RouterLink to="/" class="brand" aria-label="回到首页">
        <span class="brand-mark" aria-hidden="true"></span>
        <span class="brand-text">Sway<em>Rift</em></span>
      </RouterLink>

      <nav class="nav-links" aria-label="主导航">
        <RouterLink
          v-for="link in links"
          :key="link.to"
          :to="link.to"
          class="nav-link"
          :class="{ active: isActive(link.to) }"
        >
          {{ link.name }}
        </RouterLink>
      </nav>
    </div>
  </header>
</template>

<style scoped>
.nav {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 50;
  height: var(--nav-h);
  display: flex;
  align-items: center;
  background: rgba(10, 8, 7, 0.72);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border-bottom: 1px solid var(--line);
  animation: nav-in 0.7s cubic-bezier(0.22, 0.61, 0.36, 1);
}

@keyframes nav-in {
  from {
    opacity: 0;
    transform: translateY(-100%);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

.nav-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.brand-mark {
  width: 10px;
  height: 10px;
  border-radius: 3px;
  background: var(--grad);
  box-shadow: 0 0 14px rgba(255, 122, 26, 0.8);
  transform: rotate(45deg);
  transition: transform 0.5s cubic-bezier(0.22, 0.61, 0.36, 1);
}

.brand:hover .brand-mark {
  transform: rotate(225deg);
}

.brand-text {
  font-family: var(--font-serif);
  font-size: 1.22rem;
  font-weight: 900;
  letter-spacing: 0.02em;
}

.brand-text em {
  font-style: normal;
  background: var(--grad);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 30px;
}

.nav-link {
  position: relative;
  font-size: 0.92rem;
  color: var(--muted);
  padding: 6px 2px;
  transition: color 0.25s ease;
}

.nav-link::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 2px;
  border-radius: 2px;
  background: var(--grad);
  transform: scaleX(0);
  transform-origin: left;
  transition: transform 0.35s cubic-bezier(0.22, 0.61, 0.36, 1);
}

.nav-link:hover {
  color: var(--text);
}

.nav-link.active {
  color: var(--orange-hi);
}

.nav-link.active::after,
.nav-link:hover::after {
  transform: scaleX(1);
}

@media (max-width: 560px) {
  .nav-links {
    gap: 18px;
  }
}
</style>
