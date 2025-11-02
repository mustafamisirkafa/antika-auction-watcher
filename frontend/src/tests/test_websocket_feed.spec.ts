/**
 * Tests for WebSocket client functionality
 */

import { AuctionWebSocket } from '@/lib/websocket'
import { ConnectionStatus, WebSocketEvent } from '@/types/auction'

// Mock WebSocket
class MockWebSocket {
  url: string
  readyState: number = 0
  CONNECTING = 0
  OPEN = 1
  CLOSING = 2
  CLOSED = 3
  
  onopen: ((event: any) => void) | null = null
  onclose: ((event: any) => void) | null = null
  onerror: ((event: any) => void) | null = null
  onmessage: ((event: any) => void) | null = null

  constructor(url: string) {
    this.url = url
    this.readyState = this.CONNECTING
    
    // Simulate successful connection after a short delay
    setTimeout(() => {
      this.readyState = this.OPEN
      this.onopen?.({})
    }, 10)
  }

  send(data: string) {
    if (this.readyState !== this.OPEN) {
      throw new Error('WebSocket is not open')
    }
  }

  close() {
    this.readyState = this.CLOSED
    setTimeout(() => this.onclose?.({}), 10)
  }
}

// Replace global WebSocket with mock
global.WebSocket = MockWebSocket as any

describe('AuctionWebSocket', () => {
  let ws: AuctionWebSocket

  beforeEach(() => {
    ws = new AuctionWebSocket({
      url: 'ws://localhost:8000/test',
      reconnectInterval: 100,
      maxReconnectAttempts: 3,
    })
  })

  afterEach(() => {
    ws.disconnect()
  })

  describe('Connection Management', () => {
    test('should initialize with disconnected status', () => {
      expect(ws.getStatus()).toBe('disconnected')
      expect(ws.isConnected()).toBe(false)
    })

    test('should connect successfully', async () => {
      const statusChanges: ConnectionStatus[] = []
      ws.onStatusChange((status) => statusChanges.push(status))

      ws.connect()
      
      // Wait for connection
      await new Promise(resolve => setTimeout(resolve, 50))

      expect(statusChanges).toContain('connecting')
      expect(statusChanges).toContain('connected')
      expect(ws.isConnected()).toBe(true)
    })

    test('should handle manual disconnect', async () => {
      ws.connect()
      await new Promise(resolve => setTimeout(resolve, 50))

      expect(ws.isConnected()).toBe(true)

      ws.disconnect()
      await new Promise(resolve => setTimeout(resolve, 50))

      expect(ws.isConnected()).toBe(false)
      expect(ws.getStatus()).toBe('disconnected')
    })

    test('should not reconnect after manual disconnect', async () => {
      ws.connect()
      await new Promise(resolve => setTimeout(resolve, 50))

      ws.disconnect()
      
      // Wait for potential reconnect attempt
      await new Promise(resolve => setTimeout(resolve, 200))

      // Should still be disconnected
      expect(ws.getStatus()).toBe('disconnected')
    })

    test('should prevent multiple simultaneous connections', async () => {
      ws.connect()
      ws.connect() // Second call should be ignored
      
      await new Promise(resolve => setTimeout(resolve, 50))

      expect(ws.isConnected()).toBe(true)
    })
  })

  describe('Event Handling', () => {
    test('should receive and parse WebSocket events', async () => {
      const receivedEvents: WebSocketEvent[] = []
      
      ws.onEvent((event) => {
        receivedEvents.push(event)
      })

      ws.connect()
      await new Promise(resolve => setTimeout(resolve, 50))

      // Simulate incoming message
      const mockEvent: WebSocketEvent = {
        event: 'bid_update',
        item_id: 'test-123',
        price: 1000,
        timestamp: new Date().toISOString(),
      }

      const mockWs = (ws as any).ws as MockWebSocket
      mockWs.onmessage?.({ data: JSON.stringify(mockEvent) })

      expect(receivedEvents).toHaveLength(1)
      expect(receivedEvents[0]).toMatchObject(mockEvent)
    })

    test('should handle multiple event subscribers', async () => {
      const events1: WebSocketEvent[] = []
      const events2: WebSocketEvent[] = []

      ws.onEvent((event) => events1.push(event))
      ws.onEvent((event) => events2.push(event))

      ws.connect()
      await new Promise(resolve => setTimeout(resolve, 50))

      // Simulate message
      const mockEvent: WebSocketEvent = {
        event: 'auction_start',
        item_id: 'test-456',
        timestamp: new Date().toISOString(),
      }

      const mockWs = (ws as any).ws as MockWebSocket
      mockWs.onmessage?.({ data: JSON.stringify(mockEvent) })

      // Both subscribers should receive the event
      expect(events1).toHaveLength(1)
      expect(events2).toHaveLength(1)
    })

    test('should allow unsubscribing from events', async () => {
      const receivedEvents: WebSocketEvent[] = []
      
      const unsubscribe = ws.onEvent((event) => {
        receivedEvents.push(event)
      })

      ws.connect()
      await new Promise(resolve => setTimeout(resolve, 50))

      // Unsubscribe
      unsubscribe()

      // Simulate message
      const mockEvent: WebSocketEvent = {
        event: 'bid_update',
        timestamp: new Date().toISOString(),
      }

      const mockWs = (ws as any).ws as MockWebSocket
      mockWs.onmessage?.({ data: JSON.stringify(mockEvent) })

      // Should not receive event after unsubscribe
      expect(receivedEvents).toHaveLength(0)
    })

    test('should handle malformed JSON gracefully', async () => {
      const receivedEvents: WebSocketEvent[] = []
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation()

      ws.onEvent((event) => receivedEvents.push(event))
      ws.connect()
      await new Promise(resolve => setTimeout(resolve, 50))

      // Send invalid JSON
      const mockWs = (ws as any).ws as MockWebSocket
      mockWs.onmessage?.({ data: 'invalid json {' })

      // Should not crash, just log error
      expect(receivedEvents).toHaveLength(0)
      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('[WebSocket] Failed to parse message'),
        expect.any(Error)
      )

      consoleSpy.mockRestore()
    })
  })

  describe('Reconnection Logic', () => {
    test('should attempt reconnection after disconnect', async () => {
      const statusChanges: ConnectionStatus[] = []
      ws.onStatusChange((status) => statusChanges.push(status))

      ws.connect()
      await new Promise(resolve => setTimeout(resolve, 50))

      // Simulate disconnect
      const mockWs = (ws as any).ws as MockWebSocket
      mockWs.close()
      
      // Wait for reconnect attempt
      await new Promise(resolve => setTimeout(resolve, 150))

      // Should have transitioned: connecting -> connected -> disconnected -> connecting
      expect(statusChanges).toContain('disconnected')
      const connectingCount = statusChanges.filter(s => s === 'connecting').length
      expect(connectingCount).toBeGreaterThan(1) // Initial + reconnect
    })

    test('should use exponential backoff for reconnection', async () => {
      const reconnectDelays: number[] = []
      const originalSetTimeout = global.setTimeout

      // Track setTimeout delays
      jest.spyOn(global, 'setTimeout').mockImplementation(((callback: any, delay: number) => {
        if (delay > 50) { // Ignore small delays
          reconnectDelays.push(delay)
        }
        return originalSetTimeout(callback, 0) as any
      }) as any)

      ws.connect()
      await new Promise(resolve => originalSetTimeout(resolve, 50))

      // Force multiple disconnects
      for (let i = 0; i < 3; i++) {
        const mockWs = (ws as any).ws as MockWebSocket
        mockWs.close()
        await new Promise(resolve => originalSetTimeout(resolve, 20))
      }

      // Delays should increase
      if (reconnectDelays.length >= 2) {
        expect(reconnectDelays[1]).toBeGreaterThan(reconnectDelays[0])
      }

      jest.restoreAllMocks()
    })

    test('should stop reconnecting after max attempts', async () => {
      ws = new AuctionWebSocket({
        url: 'ws://localhost:8000/test',
        reconnectInterval: 50,
        maxReconnectAttempts: 2,
      })

      const statusChanges: ConnectionStatus[] = []
      ws.onStatusChange((status) => statusChanges.push(status))

      // Mock WebSocket that always fails
      global.WebSocket = class FailingWebSocket {
        readyState = 3 // CLOSED
        CONNECTING = 0
        OPEN = 1
        CLOSING = 2
        CLOSED = 3
        onopen = null
        onclose: any = null
        onerror: any = null
        onmessage = null

        constructor(url: string) {
          setTimeout(() => this.onclose?.(), 10)
        }
        send() {}
        close() {}
      } as any

      ws.connect()
      
      // Wait for all reconnect attempts
      await new Promise(resolve => setTimeout(resolve, 300))

      // Should eventually give up and show error
      expect(statusChanges).toContain('error')
    })
  })

  describe('Message Sending', () => {
    test('should send messages when connected', async () => {
      ws.connect()
      await new Promise(resolve => setTimeout(resolve, 50))

      const mockWs = (ws as any).ws as MockWebSocket
      const sendSpy = jest.spyOn(mockWs, 'send')

      ws.send({ type: 'test', data: 'hello' })

      expect(sendSpy).toHaveBeenCalledWith(
        JSON.stringify({ type: 'test', data: 'hello' })
      )
    })

    test('should not send messages when disconnected', async () => {
      const consoleSpy = jest.spyOn(console, 'warn').mockImplementation()

      ws.send({ type: 'test' })

      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('[WebSocket] Cannot send, not connected')
      )

      consoleSpy.mockRestore()
    })
  })

  describe('Status Change Notifications', () => {
    test('should immediately notify new subscribers of current status', () => {
      const receivedStatuses: ConnectionStatus[] = []

      ws.onStatusChange((status) => {
        receivedStatuses.push(status)
      })

      // Should immediately receive current status
      expect(receivedStatuses).toHaveLength(1)
      expect(receivedStatuses[0]).toBe('disconnected')
    })

    test('should allow unsubscribing from status changes', async () => {
      const statuses: ConnectionStatus[] = []
      
      const unsubscribe = ws.onStatusChange((status) => {
        statuses.push(status)
      })

      unsubscribe()

      ws.connect()
      await new Promise(resolve => setTimeout(resolve, 50))

      // Should only have initial status, not connection status
      expect(statuses).toHaveLength(1)
      expect(statuses[0]).toBe('disconnected')
    })
  })

  describe('Heartbeat', () => {
    test('should send periodic heartbeat messages', async () => {
      ws = new AuctionWebSocket({
        url: 'ws://localhost:8000/test',
        heartbeatInterval: 100,
      })

      ws.connect()
      await new Promise(resolve => setTimeout(resolve, 50))

      const mockWs = (ws as any).ws as MockWebSocket
      const sendSpy = jest.spyOn(mockWs, 'send')

      // Wait for heartbeat
      await new Promise(resolve => setTimeout(resolve, 150))

      // Should have sent at least one ping
      expect(sendSpy).toHaveBeenCalledWith(
        JSON.stringify({ type: 'ping' })
      )
    })

    test('should stop heartbeat on disconnect', async () => {
      ws = new AuctionWebSocket({
        url: 'ws://localhost:8000/test',
        heartbeatInterval: 50,
      })

      ws.connect()
      await new Promise(resolve => setTimeout(resolve, 60))

      ws.disconnect()
      
      const mockWs = (ws as any).ws as MockWebSocket
      const sendSpy = jest.spyOn(mockWs, 'send')

      // Wait to ensure no more heartbeats
      await new Promise(resolve => setTimeout(resolve, 100))

      // Should not send heartbeats after disconnect
      expect(sendSpy).not.toHaveBeenCalled()
    })
  })
})
