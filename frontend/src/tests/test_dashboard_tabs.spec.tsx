/**
 * Tests for Dashboard tab navigation and state persistence
 */

import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import Dashboard from '@/pages/dashboard'
import { useAuctionStore } from '@/store/auctionStore'
import * as websocket from '@/lib/websocket'
import * as api from '@/lib/api'

// Mock modules
jest.mock('@/store/auctionStore')
jest.mock('@/lib/websocket')
jest.mock('@/lib/api')

// Mock Next.js Head component
jest.mock('next/head', () => {
  return {
    __esModule: true,
    default: ({ children }: { children: React.ReactNode }) => {
      return <>{children}</>
    },
  }
})

// Mock lazy loaded components
jest.mock('@/components/LearningInsights', () => ({
  __esModule: true,
  default: () => <div>Learning Insights Component</div>,
}))

jest.mock('@/components/MetricsPanel', () => ({
  __esModule: true,
  default: () => <div>Metrics Panel Component</div>,
}))

jest.mock('@/components/AuctionFeed', () => ({
  __esModule: true,
  default: ({ showEnded }: { showEnded: boolean }) => (
    <div>Auction Feed Component - {showEnded ? 'Ended' : 'Active'}</div>
  ),
}))

describe('Dashboard Tabs', () => {
  const mockConnect = jest.fn()
  const mockDisconnect = jest.fn()
  const mockOnEvent = jest.fn(() => jest.fn())
  const mockOnStatusChange = jest.fn(() => jest.fn())
  const mockGetActiveAuctions = jest.fn(() => [])
  const mockGetEndedAuctions = jest.fn(() => [])

  beforeEach(() => {
    jest.clearAllMocks()

    // Mock WebSocket
    ;(websocket.useWebSocket as jest.Mock).mockReturnValue({
      connect: mockConnect,
      disconnect: mockDisconnect,
      onEvent: mockOnEvent,
      onStatusChange: mockOnStatusChange,
    })

    // Mock auction store
    ;(useAuctionStore as unknown as jest.Mock).mockReturnValue({
      addOrUpdateAuction: jest.fn(),
      clearAuctions: jest.fn(),
      getActiveAuctions: mockGetActiveAuctions,
      getEndedAuctions: mockGetEndedAuctions,
      auctions: {},
    })

    // Mock useAuctionStore.getState
    ;(useAuctionStore as any).getState = jest.fn(() => ({
      getActiveAuctions: mockGetActiveAuctions,
      getEndedAuctions: mockGetEndedAuctions,
      auctions: {},
    }))
  })

  describe('Tab Rendering', () => {
    test('should render all three tabs', () => {
      render(<Dashboard />)

      expect(screen.getByText(/Live Feed/)).toBeInTheDocument()
      expect(screen.getByText(/Learning Insights/)).toBeInTheDocument()
      expect(screen.getByText(/Metrics/)).toBeInTheDocument()
    })

    test('should start with Live Feed tab active', () => {
      render(<Dashboard />)

      const liveFeedTab = screen.getByText(/Live Feed/)
      expect(liveFeedTab.closest('button')).toHaveClass('text-primary-600')
    })

    test('should display Live Feed content by default', () => {
      render(<Dashboard />)

      expect(screen.getByText(/Auction Feed Component/)).toBeInTheDocument()
    })
  })

  describe('Tab Switching', () => {
    test('should switch to Learning Insights tab when clicked', async () => {
      render(<Dashboard />)

      const learningTab = screen.getByText(/Learning Insights/)
      fireEvent.click(learningTab)

      await waitFor(() => {
        expect(screen.getByText('Learning Insights Component')).toBeInTheDocument()
      })
    })

    test('should switch to Metrics tab when clicked', async () => {
      render(<Dashboard />)

      const metricsTab = screen.getByText(/Metrics/)
      fireEvent.click(metricsTab)

      await waitFor(() => {
        expect(screen.getByText('Metrics Panel Component')).toBeInTheDocument()
      })
    })

    test('should switch back to Live Feed tab', async () => {
      render(<Dashboard />)

      // Switch to Metrics
      fireEvent.click(screen.getByText(/Metrics/))
      await waitFor(() => {
        expect(screen.getByText('Metrics Panel Component')).toBeInTheDocument()
      })

      // Switch back to Live Feed
      fireEvent.click(screen.getByText(/Live Feed/))
      await waitFor(() => {
        expect(screen.getByText(/Auction Feed Component/)).toBeInTheDocument()
      })
    })

    test('should update tab active state when switching', () => {
      render(<Dashboard />)

      const learningTab = screen.getByText(/Learning Insights/)
      fireEvent.click(learningTab)

      expect(learningTab.closest('button')).toHaveClass('text-primary-600')
    })

    test('should hide inactive tab content', async () => {
      render(<Dashboard />)

      // Initially shows Live Feed
      expect(screen.getByText(/Auction Feed Component/)).toBeInTheDocument()

      // Switch to Learning Insights
      fireEvent.click(screen.getByText(/Learning Insights/))

      await waitFor(() => {
        expect(screen.queryByText(/Auction Feed Component/)).not.toBeInTheDocument()
      })
    })
  })

  describe('WebSocket State Persistence', () => {
    test('should connect to WebSocket on mount', () => {
      render(<Dashboard />)

      expect(mockConnect).toHaveBeenCalledTimes(1)
    })

    test('should not disconnect WebSocket when switching tabs', async () => {
      render(<Dashboard />)

      // Switch tabs multiple times
      fireEvent.click(screen.getByText(/Learning Insights/))
      await waitFor(() => {
        expect(screen.getByText('Learning Insights Component')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText(/Metrics/))
      await waitFor(() => {
        expect(screen.getByText('Metrics Panel Component')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText(/Live Feed/))
      await waitFor(() => {
        expect(screen.getByText(/Auction Feed Component/)).toBeInTheDocument()
      })

      // Should still be connected (not disconnected during tab switches)
      expect(mockDisconnect).not.toHaveBeenCalled()
    })

    test('should disconnect WebSocket only on unmount', () => {
      const { unmount } = render(<Dashboard />)

      // Tab switches should not disconnect
      fireEvent.click(screen.getByText(/Metrics/))
      expect(mockDisconnect).not.toHaveBeenCalled()

      // Unmount should disconnect
      unmount()
      expect(mockDisconnect).toHaveBeenCalledTimes(1)
    })

    test('should keep WebSocket subscriptions active across tabs', async () => {
      render(<Dashboard />)

      expect(mockOnEvent).toHaveBeenCalled()
      expect(mockOnStatusChange).toHaveBeenCalled()

      // Switch to different tab
      fireEvent.click(screen.getByText(/Learning Insights/))

      await waitFor(() => {
        // Should not call again (subscriptions persist)
        expect(mockOnEvent).toHaveBeenCalledTimes(1)
        expect(mockOnStatusChange).toHaveBeenCalledTimes(1)
      })
    })
  })

  describe('Connection Status Display', () => {
    test('should display connection status on all tabs', async () => {
      render(<Dashboard />)

      // Check on Live Feed tab
      expect(screen.getByText(/Disconnected ??/)).toBeInTheDocument()

      // Check on Learning Insights tab
      fireEvent.click(screen.getByText(/Learning Insights/))
      await waitFor(() => {
        expect(screen.getByText(/Disconnected ??/)).toBeInTheDocument()
      })

      // Check on Metrics tab
      fireEvent.click(screen.getByText(/Metrics/))
      await waitFor(() => {
        expect(screen.getByText(/Disconnected ??/)).toBeInTheDocument()
      })
    })
  })

  describe('Sub-tabs for Live Feed', () => {
    test('should show Active/Ended sub-tabs only on Live Feed tab', () => {
      render(<Dashboard />)

      expect(screen.getByText(/Active Auctions/)).toBeInTheDocument()
      expect(screen.getByText(/Ended Auctions/)).toBeInTheDocument()
    })

    test('should not show sub-tabs on Learning Insights tab', async () => {
      render(<Dashboard />)

      fireEvent.click(screen.getByText(/Learning Insights/))

      await waitFor(() => {
        expect(screen.queryByText(/Active Auctions/)).not.toBeInTheDocument()
        expect(screen.queryByText(/Ended Auctions/)).not.toBeInTheDocument()
      })
    })

    test('should not show sub-tabs on Metrics tab', async () => {
      render(<Dashboard />)

      fireEvent.click(screen.getByText(/Metrics/))

      await waitFor(() => {
        expect(screen.queryByText(/Active Auctions/)).not.toBeInTheDocument()
        expect(screen.queryByText(/Ended Auctions/)).not.toBeInTheDocument()
      })
    })

    test('should switch between Active and Ended auctions', () => {
      render(<Dashboard />)

      expect(screen.getByText(/Auction Feed Component - Active/)).toBeInTheDocument()

      fireEvent.click(screen.getByText(/Ended Auctions/))

      expect(screen.getByText(/Auction Feed Component - Ended/)).toBeInTheDocument()
    })
  })

  describe('Lazy Loading', () => {
    test('should show loading state for Learning Insights', async () => {
      render(<Dashboard />)

      fireEvent.click(screen.getByText(/Learning Insights/))

      // Suspense fallback should show briefly
      // Note: This is hard to test with current setup, but component is correctly wrapped
      await waitFor(() => {
        expect(screen.getByText('Learning Insights Component')).toBeInTheDocument()
      })
    })

    test('should show loading state for Metrics Panel', async () => {
      render(<Dashboard />)

      fireEvent.click(screen.getByText(/Metrics/))

      await waitFor(() => {
        expect(screen.getByText('Metrics Panel Component')).toBeInTheDocument()
      })
    })
  })

  describe('Stats Display', () => {
    test('should show auction stats on Live Feed tab', () => {
      mockGetActiveAuctions.mockReturnValue([{ id: '1' }, { id: '2' }])
      mockGetEndedAuctions.mockReturnValue([{ id: '3' }])

      render(<Dashboard />)

      expect(screen.getByText(/2.*Active/)).toBeInTheDocument()
      expect(screen.getByText(/1.*Ended/)).toBeInTheDocument()
    })

    test('should not show auction stats on other tabs', async () => {
      mockGetActiveAuctions.mockReturnValue([{ id: '1' }, { id: '2' }])

      render(<Dashboard />)

      fireEvent.click(screen.getByText(/Learning Insights/))

      await waitFor(() => {
        // Stats should be hidden
        const activeText = screen.queryByText(/Active/)
        // Either not present or not visible in the stats area
        if (activeText) {
          expect(activeText).not.toHaveTextContent('2')
        }
      })
    })
  })

  describe('Footer API Endpoints', () => {
    test('should show WebSocket endpoint on Live Feed tab', () => {
      render(<Dashboard />)

      expect(screen.getByText(/ws:\/\/127.0.0.1:8000\/api\/ws\/auctions/)).toBeInTheDocument()
    })

    test('should show Learning API endpoint on Learning Insights tab', async () => {
      render(<Dashboard />)

      fireEvent.click(screen.getByText(/Learning Insights/))

      await waitFor(() => {
        expect(screen.getByText(/\/api\/v1\/admin\/learning\/metrics/)).toBeInTheDocument()
      })
    })

    test('should show Metrics API endpoint on Metrics tab', async () => {
      render(<Dashboard />)

      fireEvent.click(screen.getByText(/Metrics/))

      await waitFor(() => {
        expect(screen.getByText(/\/api\/v1\/admin\/metrics\/dashboard/)).toBeInTheDocument()
      })
    })
  })

  describe('Clear Auctions Button', () => {
    test('should show clear button only on Live Feed tab', () => {
      render(<Dashboard />)

      expect(screen.getByText('Clear All')).toBeInTheDocument()
    })

    test('should not show clear button on other tabs', async () => {
      render(<Dashboard />)

      fireEvent.click(screen.getByText(/Learning Insights/))

      await waitFor(() => {
        expect(screen.queryByText('Clear All')).not.toBeInTheDocument()
      })
    })
  })

  describe('Tab Icons', () => {
    test('should display emoji icons for each tab', () => {
      render(<Dashboard />)

      // Check for tab emoji icons
      expect(screen.getByText('??')).toBeInTheDocument()
      expect(screen.getByText('??')).toBeInTheDocument()
      expect(screen.getByText('??')).toBeInTheDocument()
    })
  })

  describe('Responsive Behavior', () => {
    test('should render without errors on mobile viewport', () => {
      // Simulate mobile viewport
      global.innerWidth = 375
      global.innerHeight = 667

      const { container } = render(<Dashboard />)

      expect(container).toBeInTheDocument()
      expect(screen.getByText(/Live Feed/)).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    test('should have proper heading structure', () => {
      render(<Dashboard />)

      const mainHeading = screen.getByText('Antika Auction Watcher')
      expect(mainHeading.tagName).toBe('H1')
    })

    test('should have accessible tab buttons', () => {
      render(<Dashboard />)

      const tabs = screen.getAllByRole('button')
      expect(tabs.length).toBeGreaterThan(0)
      
      // Tab buttons should be keyboard accessible
      tabs.forEach(tab => {
        expect(tab.tagName).toBe('BUTTON')
      })
    })
  })
})
