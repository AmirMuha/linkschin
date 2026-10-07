'use client'

import React, { useState } from 'react'
import type { Category } from '@/types/media'
import { Sparkles, Send, X } from 'lucide-react'
import { sendChatMessage } from '@/lib/api'

const OFFLINE_ERROR = 'اتصال به سرور برقرار نشد. لطفا بعدا دوباره تلاش کنید.'

interface AiAssistantProps {
  category: Category
  isOpen: boolean
  onToggle: () => void
  onClose: () => void
}

interface ChatMessage {
  id: string
  role: 'user' | 'bot'
  text: string
}

const CHIPS = [
  'کدام فیلم ۱۰۸۰p دوبله فارسی دارد؟',
  'Show me the release with a missing part',
  'Which sources are down right now?',
  'Give me the 320 kbps link',
]

export function AiAssistant({ category, isOpen, onToggle, onClose }: AiAssistantProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'bot',
      text: 'سلام! دستیار جستجوی لینک‌چین هستم. می‌توانید درباره کیفیت‌ها، وضعیت منابع، یا پارت‌های بازی بپرسید.',
    },
  ])
  const [input, setInput] = useState('')

  async function handleSend(text: string) {
    const trimmed = text.trim()
    if (!trimmed) return

    const userMsg: ChatMessage = {
      id: String(Date.now()),
      role: 'user',
      text: trimmed,
    }

    setMessages((prev) => [...prev, userMsg])
    setInput('')

    try {
      const res = await sendChatMessage(trimmed, undefined, category)
      const botMsg: ChatMessage = {
        id: String(Date.now() + 1),
        role: 'bot',
        text: res.message || OFFLINE_ERROR,
      }
      setMessages((prev) => [...prev, botMsg])
    } catch {
      const botMsg: ChatMessage = {
        id: String(Date.now() + 1),
        role: 'bot',
        text: OFFLINE_ERROR,
      }
      setMessages((prev) => [...prev, botMsg])
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    handleSend(input)
  }

  return (
    <>
      <button
        className="chat-fab"
        type="button"
        aria-expanded={isOpen}
        aria-controls="chat"
        onClick={onToggle}
      >
        <Sparkles className="w-4 h-4" />
        <span>Ask AI</span>
      </button>

      <section
        className={`chat ${isOpen ? 'on' : ''}`}
        id="chat"
        aria-label="AI search assistant"
      >
        <div className="chat-head">
          <div>
            <strong>Search assistant</strong>
            <span>reads active category ({category})</span>
          </div>
          <button
            className="btn btn-quiet btn-sm"
            type="button"
            onClick={onClose}
            aria-label="Close assistant"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="chat-log" role="log" aria-live="polite">
          {messages.map((m) => (
            <div
              key={m.id}
              className={`p-2.5 rounded-xl text-xs max-w-[85%] leading-relaxed ${
                m.role === 'user'
                  ? 'bg-zinc-800 text-white self-end ms-auto'
                  : 'bg-zinc-900/90 text-zinc-200 border border-white/10 self-start'
              }`}
            >
              {m.text}
            </div>
          ))}
        </div>

        <div className="chips" style={{ padding: '8px 12px', overflowX: 'auto', flexWrap: 'nowrap' }}>
          {CHIPS.map((chip, idx) => (
            <button
              key={idx}
              type="button"
              className="chip shrink-0 text-xs"
              onClick={() => handleSend(chip)}
            >
              {chip}
            </button>
          ))}
        </div>

        <form className="chat-form" onSubmit={handleSubmit}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask in Persian or English…"
            aria-label="Message the assistant"
          />
          <button
            className="btn btn-primary btn-sm"
            type="submit"
            aria-label="Send"
            disabled={!input.trim()}
          >
            <Send className="w-3.5 h-3.5" />
          </button>
        </form>
      </section>
    </>
  )
}
