/**
 * v-reveal 指令：元素进入视口时播放上浮入场动画。
 * 用法：v-reveal="120"（数值为延迟毫秒数，可省略）。
 */

const OBSERVERS = new WeakMap()

export const reveal = {
  mounted(el, binding) {
    el.classList.add('reveal-scroll')
    const delay = Number(binding.value || 0)
    if (delay > 0) {
      el.style.setProperty('--reveal-delay', `${delay}ms`)
    }
    const io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add('reveal-in')
            io.unobserve(entry.target)
          }
        }
      },
      { threshold: 0.12, rootMargin: '0px 0px -30px 0px' },
    )
    io.observe(el)
    OBSERVERS.set(el, io)
  },
  unmounted(el) {
    const io = OBSERVERS.get(el)
    if (io) {
      io.disconnect()
      OBSERVERS.delete(el)
    }
  },
}
