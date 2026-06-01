import { io } from 'socket.io-client'
import { getServerUrl } from './config'

class SocketClient {
  constructor() {
    this.socket = null
    this.listeners = new Map()
    this.rooms = new Set()
  }

  async connect() {
    if (this.socket?.connected) return this.socket

    const serverUrl = await getServerUrl()
    if (!serverUrl) return null

    this.socket = io(serverUrl, {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionAttempts: 10,
    })

    this.socket.on('connect', () => {
      this.rooms.forEach(room => {
        this.socket.emit('join', { conversation_id: room })
      })
    })

    this.listeners.forEach((callbacks, event) => {
      callbacks.forEach(callback => this.socket.on(event, callback))
    })

    return this.socket
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
    }
  }

  joinConversation(conversationId) {
    if (!conversationId) return
    this.rooms.add(conversationId)
    if (this.socket?.connected) {
      this.socket.emit('join', { conversation_id: conversationId })
    }
  }

  leaveConversation(conversationId) {
    if (!conversationId) return
    this.rooms.delete(conversationId)
    if (this.socket?.connected) {
      this.socket.emit('leave', { conversation_id: conversationId })
    }
  }

  on(event, callback) {
    if (!this.listeners.has(event)) this.listeners.set(event, [])
    this.listeners.get(event).push(callback)
    if (this.socket) this.socket.on(event, callback)
  }

  off(event, callback) {
    if (this.listeners.has(event)) {
      this.listeners.set(event, this.listeners.get(event).filter(item => item !== callback))
    }
    if (this.socket) this.socket.off(event, callback)
  }
}

export default new SocketClient()
