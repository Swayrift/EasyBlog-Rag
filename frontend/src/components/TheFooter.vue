<script setup>
const year = new Date().getFullYear()
</script>

<template>
  <footer class="footer">
    <div class="container footer-inner">
      <div class="footer-rule" aria-hidden="true"></div>
      <div class="footer-row">
        <p class="footer-main">© {{ year }} SwayRift · 把技术思考沉淀成文字</p>
        <p class="footer-sub">FastAPI · Vue 3 · SQLite · FAISS</p>
      </div>
    </div>
  </footer>
</template>

<style scoped>
.footer {
  margin-top: 96px;
  padding-bottom: 42px;
  position: relative;
  z-index: 1;
}

.footer-rule {
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--line-strong) 30%, rgba(255, 122, 26, 0.45) 50%, var(--line-strong) 70%, transparent);
  margin-bottom: 28px;
}

.footer-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.footer-main {
  font-size: 0.88rem;
  color: var(--muted);
}

.footer-sub {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  letter-spacing: 0.14em;
  color: var(--faint);
}
</style>
