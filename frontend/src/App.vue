<script setup>
import { RouterView, useRoute } from 'vue-router'
import TheNavbar from '@/components/TheNavbar.vue'
import TheFooter from '@/components/TheFooter.vue'

const route = useRoute()
</script>

<template>
  <div class="app-shell">
    <!-- 背景光晕与噪点 -->
    <div class="ember ember-a" aria-hidden="true"></div>
    <div class="ember ember-b" aria-hidden="true"></div>
    <div class="grain" aria-hidden="true"></div>

    <TheNavbar v-if="!route.meta.bare" />

    <main class="app-main">
      <RouterView v-slot="{ Component, route: view }">
        <transition name="page" mode="out-in">
          <component :is="Component" :key="view.path" />
        </transition>
      </RouterView>
    </main>

    <TheFooter v-if="!route.meta.bare && !route.meta.hideFooter" />
  </div>
</template>

<style>
.app-shell {
  position: relative;
  min-height: 100vh;
}

.app-main {
  position: relative;
  z-index: 1;
}

/* ---------- 背景余烬光晕 ---------- */
.ember {
  position: fixed;
  border-radius: 50%;
  filter: blur(90px);
  pointer-events: none;
  z-index: 0;
}

.ember-a {
  width: 540px;
  height: 540px;
  top: -200px;
  right: -140px;
  background: radial-gradient(circle, rgba(255, 122, 26, 0.16), transparent 65%);
  animation: drift-a 16s ease-in-out infinite alternate;
}

.ember-b {
  width: 460px;
  height: 460px;
  bottom: -180px;
  left: -160px;
  background: radial-gradient(circle, rgba(224, 78, 0, 0.13), transparent 65%);
  animation: drift-b 20s ease-in-out infinite alternate;
}

@keyframes drift-a {
  from {
    transform: translate3d(0, 0, 0) scale(1);
  }
  to {
    transform: translate3d(-50px, 40px, 0) scale(1.1);
  }
}

@keyframes drift-b {
  from {
    transform: translate3d(0, 0, 0) scale(1.05);
  }
  to {
    transform: translate3d(46px, -34px, 0) scale(0.95);
  }
}

/* ---------- 噪点纹理 ---------- */
.grain {
  position: fixed;
  inset: 0;
  z-index: 60;
  pointer-events: none;
  opacity: 0.05;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160' viewBox='0 0 160 160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}

@media (prefers-reduced-motion: reduce) {
  .ember-a,
  .ember-b {
    animation: none;
  }
}
</style>
