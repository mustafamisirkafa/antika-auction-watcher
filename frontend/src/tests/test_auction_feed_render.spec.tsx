/**
 * Tests for AuctionFeed component rendering and updates
 */

import React from 'react'
import { render, screen, waitFor, act } from '@testing-library/react'
import '@testing-library/jest-dom'
import AuctionFeed from '@/components/AuctionFeed'
import { useAuctionStore } from '@/store/auctionStore'

// Mock the store
jest.mock('@/store/auctionStore')

describe('AuctionFeed Component', () => {
  const mockGetActiveAuctions = jest.fn()
  const mockGetEndedAuctions = jest.fn()
  const mockRecentlyUpdated = new Set<string>()

  beforeEach(() => {
    jest.clearAllMocks()
    ;(useAuctionStore as unknown as jest.Mock).mockReturnValue({
      getActiveAuctions: mockGetActiveAuctions,
      getEndedAuctions: mockGetEndedAuctions,
      recentlyUpdated: mockRecentlyUpdated,
    })
  })

  describe('Empty State', () => {
    test('should show empty state when no auctions', () => {
      mockGetActiveAuctions.mockReturnValue([])
      mockGetEndedAuctions.mockReturnValue([])

      render(<AuctionFeed />)

      expect(screen.getByText('No Live Auctions')).toBeInTheDocument()
      expect(
        screen.getByText(/Waiting for live auction data/i)
      ).toBeInTheDocument()
    })

    test('should show empty ended auctions message', () => {
      mockGetActiveAuctions.mockReturnValue([])
      mockGetEndedAuctions.mockReturnValue([])

      render(<AuctionFeed showEnded={true} />)

      expect(screen.getByText('No Ended Auctions Yet')).toBeInTheDocument()
    })
  })

  describe('Active Auctions Display', () => {
    test('should render active auctions', () => {
      const mockAuctions = [
        {
          id: 'AUC-1',
          title: 'Vintage Watch',
          currentPrice: 1000,
          status: 'active' as const,
          lastBidAt: '2025-11-02T10:00:00Z',
          valuation: 1500,
          confidence: 0.85,
        },
        {
          id: 'AUC-2',
          title: 'Antique Vase',
          currentPrice: 500,
          status: 'active' as const,
          lastBidAt: '2025-11-02T10:05:00Z',
        },
      ]

      mockGetActiveAuctions.mockReturnValue(mockAuctions)
      mockGetEndedAuctions.mockReturnValue([])

      render(<AuctionFeed />)

      expect(screen.getByText('Vintage Watch')).toBeInTheDocument()
      expect(screen.getByText('Antique Vase')).toBeInTheDocument()
      expect(screen.getByText('Live Auctions')).toBeInTheDocument()
      expect(screen.getByText('(2)')).toBeInTheDocument()
    })

    test('should display auction prices correctly', () => {
      const mockAuctions = [
        {
          id: 'AUC-1',
          title: 'Test Item',
          currentPrice: 1280.5,
          status: 'active' as const,
          lastBidAt: '2025-11-02T10:00:00Z',
        },
      ]

      mockGetActiveAuctions.mockReturnValue(mockAuctions)
      mockGetEndedAuctions.mockReturnValue([])

      render(<AuctionFeed />)

      // Price should be formatted as Turkish Lira
      expect(screen.getByText(/1\.280,50/)).toBeInTheDocument()
    })

    test('should show active status badge', () => {
      const mockAuctions = [
        {
          id: 'AUC-1',
          title: 'Test Item',
          currentPrice: 1000,
          status: 'active' as const,
          lastBidAt: '2025-11-02T10:00:00Z',
        },
      ]

      mockGetActiveAuctions.mockReturnValue(mockAuctions)
      mockGetEndedAuctions.mockReturnValue([])

      render(<AuctionFeed />)

      expect(screen.getByText('LIVE')).toBeInTheDocument()
    })
  })

  describe('Ended Auctions Display', () => {
    test('should render ended auctions', () => {
      const mockAuctions = [
        {
          id: 'AUC-1',
          title: 'Sold Watch',
          currentPrice: 2000,
          status: 'ended' as const,
          lastBidAt: '2025-11-02T09:00:00Z',
          bidder: 'user_42',
        },
      ]

      mockGetActiveAuctions.mockReturnValue([])
      mockGetEndedAuctions.mockReturnValue(mockAuctions)

      render(<AuctionFeed showEnded={true} />)

      expect(screen.getByText('Sold Watch')).toBeInTheDocument()
      expect(screen.getByText('ENDED')).toBeInTheDocument()
      expect(screen.getByText(/user_42/)).toBeInTheDocument()
    })
  })

  describe('AI Valuation Display', () => {
    test('should show valuation and confidence when available', () => {
      const mockAuctions = [
        {
          id: 'AUC-1',
          title: 'Test Item',
          currentPrice: 1000,
          valuation: 1500,
          confidence: 0.85,
          status: 'active' as const,
          lastBidAt: '2025-11-02T10:00:00Z',
        },
      ]

      mockGetActiveAuctions.mockReturnValue(mockAuctions)
      mockGetEndedAuctions.mockReturnValue([])

      render(<AuctionFeed />)

      expect(screen.getByText('AI Valuation')).toBeInTheDocument()
      expect(screen.getByText(/1\.500,00/)).toBeInTheDocument()
      expect(screen.getByText('85%')).toBeInTheDocument()
    })

    test('should show confidence bar with correct color', () => {
      const mockAuctions = [
        {
          id: 'AUC-1',
          title: 'High Confidence',
          currentPrice: 1000,
          valuation: 1500,
          confidence: 0.9,
          status: 'active' as const,
          lastBidAt: '2025-11-02T10:00:00Z',
        },
      ]

      mockGetActiveAuctions.mockReturnValue(mockAuctions)
      mockGetEndedAuctions.mockReturnValue([])

      const { container } = render(<AuctionFeed />)

      // High confidence (>0.8) should have green color
      const confidenceBar = container.querySelector('.bg-green-500')
      expect(confidenceBar).toBeInTheDocument()
    })

    test('should show price vs valuation indicator', () => {
      const mockAuctions = [
        {
          id: 'AUC-1',
          title: 'Good Deal',
          currentPrice: 1000,
          valuation: 1500,
          confidence: 0.8,
          status: 'active' as const,
          lastBidAt: '2025-11-02T10:00:00Z',
        },
      ]

      mockGetActiveAuctions.mockReturnValue(mockAuctions)
      mockGetEndedAuctions.mockReturnValue([])

      render(<AuctionFeed />)

      // Price is ~67% of valuation, should show "below valuation"
      expect(screen.getByText(/below valuation/i)).toBeInTheDocument()
    })
  })

  describe('Bid Update Animation', () => {
    test('should apply animation class when recently updated', () => {
      const mockAuctions = [
        {
          id: 'AUC-1',
          title: 'Updated Item',
          currentPrice: 1000,
          status: 'active' as const,
          lastBidAt: '2025-11-02T10:00:00Z',
        },
      ]

      mockGetActiveAuctions.mockReturnValue(mockAuctions)
      mockGetEndedAuctions.mockReturnValue([])
      mockRecentlyUpdated.add('AUC-1')
      ;(useAuctionStore as unknown as jest.Mock).mockReturnValue({
        getActiveAuctions: mockGetActiveAuctions,
        getEndedAuctions: mockGetEndedAuctions,
        recentlyUpdated: mockRecentlyUpdated,
      })

      const { container } = render(<AuctionFeed />)

      const card = container.querySelector('.animate-bid-update')
      expect(card).toBeInTheDocument()
    })

    test('should remove animation class after timeout', async () => {
      jest.useFakeTimers()

      const mockAuctions = [
        {
          id: 'AUC-1',
          title: 'Updated Item',
          currentPrice: 1000,
          status: 'active' as const,
          lastBidAt: '2025-11-02T10:00:00Z',
        },
      ]

      mockGetActiveAuctions.mockReturnValue(mockAuctions)
      mockGetEndedAuctions.mockReturnValue([])
      mockRecentlyUpdated.add('AUC-1')
      ;(useAuctionStore as unknown as jest.Mock).mockReturnValue({
        getActiveAuctions: mockGetActiveAuctions,
        getEndedAuctions: mockGetEndedAuctions,
        recentlyUpdated: mockRecentlyUpdated,
      })

      const { container, rerender } = render(<AuctionFeed />)

      // Initially has animation
      expect(container.querySelector('.animate-bid-update')).toBeInTheDocument()

      // Simulate time passing
      act(() => {
        jest.advanceTimersByTime(600)
      })

      // Remove from recently updated
      mockRecentlyUpdated.delete('AUC-1')
      rerender(<AuctionFeed />)

      // Animation should be removed
      expect(container.querySelector('.animate-bid-update')).not.toBeInTheDocument()

      jest.useRealTimers()
    })
  })

  describe('Image Display', () => {
    test('should show image when available', () => {
      const mockAuctions = [
        {
          id: 'AUC-1',
          title: 'Item with Image',
          image: 'https://example.com/image.jpg',
          currentPrice: 1000,
          status: 'active' as const,
          lastBidAt: '2025-11-02T10:00:00Z',
        },
      ]

      mockGetActiveAuctions.mockReturnValue(mockAuctions)
      mockGetEndedAuctions.mockReturnValue([])

      render(<AuctionFeed />)

      const image = screen.getByAltText('Item with Image')
      expect(image).toBeInTheDocument()
      expect(image).toHaveAttribute('src', 'https://example.com/image.jpg')
    })

    test('should show placeholder when no image', () => {
      const mockAuctions = [
        {
          id: 'AUC-1',
          title: 'Item without Image',
          currentPrice: 1000,
          status: 'active' as const,
          lastBidAt: '2025-11-02T10:00:00Z',
        },
      ]

      mockGetActiveAuctions.mockReturnValue(mockAuctions)
      mockGetEndedAuctions.mockReturnValue([])

      const { container } = render(<AuctionFeed />)

      // Should show SVG placeholder
      const svg = container.querySelector('svg')
      expect(svg).toBeInTheDocument()
    })
  })

  describe('Category Display', () => {
    test('should show category badge when available', () => {
      const mockAuctions = [
        {
          id: 'AUC-1',
          title: 'Categorized Item',
          currentPrice: 1000,
          category: 'antiques',
          status: 'active' as const,
          lastBidAt: '2025-11-02T10:00:00Z',
        },
      ]

      mockGetActiveAuctions.mockReturnValue(mockAuctions)
      mockGetEndedAuctions.mockReturnValue([])

      render(<AuctionFeed />)

      expect(screen.getByText('antiques')).toBeInTheDocument()
    })
  })

  describe('Time Formatting', () => {
    test('should format time correctly', () => {
      const mockAuctions = [
        {
          id: 'AUC-1',
          title: 'Test Item',
          currentPrice: 1000,
          status: 'active' as const,
          lastBidAt: '2025-11-02T14:30:45Z',
        },
      ]

      mockGetActiveAuctions.mockReturnValue(mockAuctions)
      mockGetEndedAuctions.mockReturnValue([])

      render(<AuctionFeed />)

      // Should show formatted time (format depends on locale)
      expect(screen.getByText(/Last update:/)).toBeInTheDocument()
    })
  })

  describe('Grid Layout', () => {
    test('should render multiple items in grid', () => {
      const mockAuctions = Array.from({ length: 8 }, (_, i) => ({
        id: `AUC-${i}`,
        title: `Item ${i}`,
        currentPrice: 1000 + i * 100,
        status: 'active' as const,
        lastBidAt: '2025-11-02T10:00:00Z',
      }))

      mockGetActiveAuctions.mockReturnValue(mockAuctions)
      mockGetEndedAuctions.mockReturnValue([])

      const { container } = render(<AuctionFeed />)

      const grid = container.querySelector('.grid')
      expect(grid).toBeInTheDocument()
      expect(grid?.children.length).toBe(8)
    })
  })

  describe('Hover Effects', () => {
    test('should have hover classes on cards', () => {
      const mockAuctions = [
        {
          id: 'AUC-1',
          title: 'Hoverable Item',
          currentPrice: 1000,
          status: 'active' as const,
          lastBidAt: '2025-11-02T10:00:00Z',
        },
      ]

      mockGetActiveAuctions.mockReturnValue(mockAuctions)
      mockGetEndedAuctions.mockReturnValue([])

      const { container } = render(<AuctionFeed />)

      const card = container.querySelector('.hover\\:shadow-lg')
      expect(card).toBeInTheDocument()
    })
  })
})
