import '@testing-library/jest-dom'

// Mock WebSocket
global.WebSocket = class MockWebSocket {
  constructor(url) {
    this.url = url
    this.readyState = 0
    this.CONNECTING = 0
    this.OPEN = 1
    this.CLOSING = 2
    this.CLOSED = 3
  }

  send(data) {}
  close() {}
  addEventListener(event, handler) {}
  removeEventListener(event, handler) {}
}
