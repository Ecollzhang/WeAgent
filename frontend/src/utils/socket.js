import { io } from 'socket.io-client'

class SocketClient {
  constructor() {
    this.socket = null
    this.listeners = {}
  }

  connect() {
    if (this.socket && this.socket.connected) {
      return
    }

    this.socket = io('/', {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionAttempts: 10,
    })

    this.socket.on('connect', () => {
      console.log('Socket connected')
    })

    this.socket.on('disconnect', () => {
      console.log('Socket disconnected')
    })

    this.socket.on('connect_error', (error) => {
      console.error('Socket connection error:', error)
    })

    // Re-attach all listeners
    Object.keys(this.listeners).forEach(event => {
      this.listeners[event].forEach(callback => {
        this.socket.on(event, callback)
      })
    })
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
    }
  }

  joinConversation(conversationId) {
    if (this.socket && this.socket.connected) {
      this.socket.emit('join', { conversation_id: conversationId })
    }
  }

  leaveConversation(conversationId) {
    if (this.socket && this.socket.connected) {
      this.socket.emit('leave', { conversation_id: conversationId })
    }
  }

  sendMessage(data) {
    if (this.socket && this.socket.connected) {
      this.socket.emit('send_message', data)
    }
  }

  on(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = []
    }
    this.listeners[event].push(callback)

    if (this.socket) {
      this.socket.on(event, callback)
    }
  }

  off(event, callback) {
    if (this.listeners[event]) {
      this.listeners[event] = this.listeners[event].filter(cb => cb !== callback)
    }
    if (this.socket) {
      this.socket.off(event, callback)
    }
  }
}

const socketClient = new SocketClient()
export default socketClient
