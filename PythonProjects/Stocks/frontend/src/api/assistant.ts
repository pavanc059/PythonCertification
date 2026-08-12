import apiClient from './client'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export async function getChatHistory(): Promise<ChatMessage[]> {
  const res = await apiClient.get<ChatMessage[]>('/assistant/history')
  return res.data
}

export async function clearChatHistory(): Promise<void> {
  await apiClient.delete('/assistant/history')
}

/**
 * Send a message and stream back the response via SSE.
 * Calls onChunk with each text piece, then onDone when complete.
 * Uses fetch directly because axios doesn't support streaming.
 */
export async function streamChat(
  message: string,
  onChunk: (text: string) => void,
  onDone: () => void,
  onError: (err: string) => void,
): Promise<void> {
  const token = localStorage.getItem('stockiq-token')
  const baseUrl = import.meta.env.VITE_API_URL ?? '/api'

  let res: Response
  try {
    res = await fetch(`${baseUrl}/assistant/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ message }),
    })
  } catch (err) {
    onError(String(err))
    return
  }

  if (!res.ok) {
    onError(`Request failed: ${res.status}`)
    return
  }

  const reader = res.body?.getReader()
  if (!reader) {
    onError('No response body')
    return
  }

  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const payload = line.slice(6)
        if (payload === '[DONE]') {
          onDone()
          return
        }
        // Restore newlines that were escaped as <br> during streaming
        onChunk(payload.replace(/<br>/g, '\n'))
      }
    }
  }
  onDone()
}
