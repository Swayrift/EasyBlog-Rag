import { defineStore } from 'pinia'

export const useChatStore = defineStore('chat', {
  state: () => ({
    messages: [],
  }),

  getters: {
    hasPendingMessage: (state) => state.messages.some((message) => message.loading),
  },

  actions: {
    addUserMessage(content) {
      this.messages.push({ role: 'user', content })
    },

    addAssistantMessage() {
      this.messages.push({
        role: 'assistant',
        content: '',
        sources: [],
        loading: false,
        error: '',
        expanded: [],
      })
      return this.messages.length - 1
    },

    appendAssistantMessage(index, content) {
      const message = this.messages[index]
      if (!message || message.role !== 'assistant') return
      message.content += content
    },

    completeAssistantMessage(index, answer, sources) {
      const message = this.messages[index]
      if (!message || message.role !== 'assistant') return
      message.content = answer
      message.sources = sources || []
      message.expanded = message.sources.map(() => false)
    },

    setAssistantSources(index, sources) {
      const message = this.messages[index]
      if (!message || message.role !== 'assistant') return
      message.sources = sources || []
      if (!Array.isArray(message.expanded)) message.expanded = []
      message.expanded = message.sources.map((_, sourceIndex) => Boolean(message.expanded[sourceIndex]))
    },

    failAssistantMessage(index, error) {
      const message = this.messages[index]
      if (!message || message.role !== 'assistant') return
      message.error = error
    },

    finishAssistantMessage(index) {
      const message = this.messages[index]
      if (!message || message.role !== 'assistant') return
      message.loading = false
    },

    toggleSource(messageIndex, sourceIndex) {
      const message = this.messages[messageIndex]
      if (!message || message.role !== 'assistant' || !message.sources?.[sourceIndex]) return
      if (!Array.isArray(message.expanded)) message.expanded = []
      message.expanded[sourceIndex] = !message.expanded[sourceIndex]
    },

    clearConversation() {
      this.messages = []
    },
  },
})
