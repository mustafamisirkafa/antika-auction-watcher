/**
 * Tests for SystemHealth component
 */

import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import SystemHealth from '@/components/SystemHealth'
import * as api from '@/lib/api'
import { SystemMetrics } from '@/types/admin'

// Mock SWR
jest.mock('swr', () => ({
  __esModule: true,
  default: (key: string, fetcher: () => Promise<any>, options: any) => {
    const [data, setData] = React.useState<any>(null)
    const [error, setError] = React.useState<any>(null)
    const [isLoading, setIsLoading] = React.useState(true)

    React.useEffect(() => {
      if (fetcher) {
        setIsLoading(true)
        fetcher()
          .then(setData)
          .catch(setError)
          .finally(() => setIsLoading(false))
      }
    }, [])

    return {
      data,
      error,
      isLoading,
      mutate: jest.fn(),
    }
  },
}))

// Mock API
jest.mock('@/lib/api')

describe('SystemHealth Component', () => {
  const mockMetrics: SystemMetrics = {
    uptime: '5d 12h 42m',
    requests_per_second: 135,
    response_time_ms: {
      p50: 110,
      p90: 160,
      p99: 230,
    },
    redis_hit_ratio: 0.92,
    queue_pending: 14,
  }

  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('Loading State', () => {
    test('should show loading spinner', () => {
      ;(api.fetchAdminStats as jest.Mock).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      )

      render(<SystemHealth />)

      expect(screen.getByText('Loading system health...')).toBeInTheDocument()
    })
  })

  describe('Error State', () => {
    test('should display error message when API fails', async () => {
      ;(api.fetchAdminStats as jest.Mock).mockRejectedValue(
        new Error('Network error')
      )

      render(<SystemHealth />)

      await waitFor(() => {
        expect(screen.getByText('Failed to Load System Health')).toBeInTheDocument()
        expect(screen.getByText('Network error')).toBeInTheDocument()
      })
    })
  })

  describe('Data Display', () => {
    test('should display system uptime', async () => {
      ;(api.fetchAdminStats as jest.Mock).mockResolvedValue(mockMetrics)

      render(<SystemHealth />)

      await waitFor(() => {
        expect(screen.getByText('5d 12h 42m')).toBeInTheDocument()
      })
    })

    test('should display requests per second', async () => {
      ;(api.fetchAdminStats as jest.Mock).mockResolvedValue(mockMetrics)

      render(<SystemHealth />)

      await waitFor(() => {
        expect(screen.getByText('135')).toBeInTheDocument()
      })
    })

    test('should display response time p99', async () => {
      ;(api.fetchAdminStats as jest.Mock).mockResolvedValue(mockMetrics)

      render(<SystemHealth />)

      await waitFor(() => {
        expect(screen.getByText('230ms')).toBeInTheDocument()
      })
    })

    test('should display cache hit ratio', async () => {
      ;(api.fetchAdminStats as jest.Mock).mockResolvedValue(mockMetrics)

      render(<SystemHealth />)

      await waitFor(() => {
        expect(screen.getByText('92.0%')).toBeInTheDocument()
      })
    })

    test('should display queue pending', async () => {
      ;(api.fetchAdminStats as jest.Mock).mockResolvedValue(mockMetrics)

      render(<SystemHealth />)

      await waitFor(() => {
        expect(screen.getByText('14')).toBeInTheDocument()
      })
    })
  })

  describe('Auto-Refresh Indicator', () => {
    test('should show 10 second auto-refresh indicator', async () => {
      ;(api.fetchAdminStats as jest.Mock).mockResolvedValue(mockMetrics)

      render(<SystemHealth />)

      await waitFor(() => {
        expect(screen.getByText('Auto-refresh: 10s')).toBeInTheDocument()
      })
    })
  })

  describe('Color-Coded Thresholds - RPS', () => {
    test('should show green for excellent RPS (?200)', async () => {
      ;(api.fetchAdminStats as jest.Mock).mockResolvedValue({
        ...mockMetrics,
        requests_per_second: 150,
      })

      render(<SystemHealth />)

      await waitFor(() => {
        expect(screen.getByText('? Excellent')).toBeInTheDocument()
      })
    })

    test('should show blue for good RPS (200-500)', async () => {
      ;(api.fetchAdminStats as jest.Mock).mockResolvedValue({
        ...mockMetrics,
        requests_per_second: 350,
      })

      render(<SystemHealth />)

      await waitFor(() => {
        expect(screen.getByText('?? Good')).toBeInTheDocument()
      })
    })

    test('should show yellow for warning RPS (500-800)', async () => {
      ;(api.fetchAdminStats as jest.Mock).mockResolvedValue({
        ...mockMetrics,
        requests_per_second: 650,
      })

      render(<SystemHealth />)

      await waitFor(() => {
        expect(screen.getByText('?? Warning')).toBeInTheDocument()
      })
    })

    test('should show red for critical RPS (>800)', async () => {
      ;(api.fetchAdminStats as jest.Mock).mockResolvedValue({
        ...mockMetrics,
        requests_per_second: 900,
      })

      render(<SystemHealth />)

      await waitFor(() => {
        expect(screen.getByText('?? Critical')).toBeInTheDocument()
      })
    })
  })

  describe('Color-Coded Thresholds - Response Time p99', () => {
    test('should show green for excellent p99 (?200ms)', async () => {
      ;(api.fetchAdminStats as jest.Mock).mockResolvedValue({
        ...mockMetrics,
        response_time_ms: { p50: 50, p90: 100, p99: 150 },
      })

      render(<SystemHealth />)

      await waitFor(() => {
        const excellents = screen.getAllByText('? Excellent')
        expect(excellents.length).toBeGreaterThan(0)
      })
    })

    test('should show blue for good p99 (200-400ms)', async () => {
      ;(api.fetchAdminStats as jest.Mock).mockResolvedValue({
        ...mockMetrics,
        response_time_ms: { p50: 100, p90: 200, p99: 300 },
      })

      render(<SystemHealth />)

      await waitFor(() => {
        const goods = screen.getAllByText('?? Good')
        expect(goods.length).toBeGreaterThan(0)
      })
    })

    test('should show yellow for warning p99 (400-800ms)', async () => {
      ;(api.fetchAdminStats as jest.Mock).mockResolvedValue({
        ...mockMetrics,
        response_time_ms: { p50: 200, p90: 400, p99: 600 },
      })

      render(<SystemHealth />)

      await waitFor(() => {
        const warnings = screen.getAllByText('?? Warning')
        expect(warnings.length).toBeGreaterThan(0)
      })
    })

    test('should show red for critical p99 (>800ms)', async () => {
      ;(api.fetchAdminStats as jest.Mock).mockResolvedValue({
        ...mockMetrics,
        response_time_ms: { p50: 400, p90: 600, p99: 1000 },
      })

      render(<SystemHealth />)

      await waitFor(() => {
        const criticals = screen.getAllByText('?? Critical')
        expect(criticals.length).toBeGreaterThan(0)
      })
    })
  })

  describe('Color-Coded Thresholds - Cache Hit Ratio', () => {
    test('should show green for excellent cache (?90%)', async () => {
      ;(api.fetchAdminStats as jest.Mock).mockResolvedValue({
        ...mockMetrics,
        redis_hit_ratio: 0.95,
      })

      render(<SystemHealth />)

      await waitFor(() => {
        const excellents = screen.getAllByText('? Excellent')
        expect(excellents.length).toBeGreaterThan(0)
      })
    })

    test('should show blue for good cache (75-90%)', async () => {
      ;(api.fetchAdminStats as jest.Mock).mockResolvedValue({
        ...mockMetrics,
        redis_hit_ratio: 0.82,
      })

      render(<SystemHealth />)

      await waitFor(() => {
        const goods = screen.getAllByText('?? Good')
        expect(goods.length).toBeGreaterThan(0)
      })
    })

    test('should show yellow for warning cache (60-75%)', async () => {
      ;(api.fetchAdminStats as jest.Mock).mockResolvedValue({
        ...mockMetrics,
        redis_hit_ratio: 0.68,
      })

      render(<SystemHealth />)

      await waitFor(() => {
        const warnings = screen.getAllByText('?? Warning')
        expect(warnings.length).toBeGreaterThan(0)
      })
    })

    test('should show red for critical cache (<60%)', async () => {
      ;(api.fetchAdminStats as jest.Mock).mockResolvedValue({
        ...mockMetrics,
        redis_hit_ratio: 0.45,
      })

      render(<SystemHealth />)

      await waitFor(() => {
        const criticals = screen.getAllByText('?? Critical')
        expect(criticals.length).toBeGreaterThan(0)
      })
    })
  })

  describe('Color-Coded Thresholds - Queue', () => {
    test('should show green for excellent queue (?10)', async () => {
      ;(api.fetchAdminStats as jest.Mock).mockResolvedValue({
        ...mockMetrics,
        queue_pending: 5,
      })

      render(<SystemHealth />)

      await waitFor(() => {
        const excellents = screen.getAllByText('? Excellent')
        expect(excellents.length).toBeGreaterThan(0)
      })
    })

    test('should show blue for good queue (10-50)', async () => {
      ;(api.fetchAdminStats as jest.Mock).mockResolvedValue({
        ...mockMetrics,
        queue_pending: 30,
      })

      render(<SystemHealth />)

      await waitFor(() => {
        const goods = screen.getAllByText('?? Good')
        expect(goods.length).toBeGreaterThan(0)
      })
    })

    test('should show yellow for warning queue (50-100)', async () => {
      ;(api.fetchAdminStats as jest.Mock).mockResolvedValue({
        ...mockMetrics,
        queue_pending: 75,
      })

      render(<SystemHealth />)

      await waitFor(() => {
        const warnings = screen.getAllByText('?? Warning')
        expect(warnings.length).toBeGreaterThan(0)
      })
    })

    test('should show red for critical queue (>100)', async () => {
      ;(api.fetchAdminStats as jest.Mock).mockResolvedValue({
        ...mockMetrics,
        queue_pending: 150,
      })

      render(<SystemHealth />)

      await waitFor(() => {
        const criticals = screen.getAllByText('?? Critical')
        expect(criticals.length).toBeGreaterThan(0)
      })
    })
  })

  describe('Response Time Percentiles Display', () => {
    test('should display all three percentiles', async () => {
      ;(api.fetchAdminStats as jest.Mock).mockResolvedValue(mockMetrics)

      render(<SystemHealth />)

      await waitFor(() => {
        expect(screen.getByText('110ms')).toBeInTheDocument()
        expect(screen.getByText('160ms')).toBeInTheDocument()
        expect(screen.getByText('230ms')).toBeInTheDocument()
      })
    })
  })

  describe('Thresholds Legend', () => {
    test('should display performance thresholds legend', async () => {
      ;(api.fetchAdminStats as jest.Mock).mockResolvedValue(mockMetrics)

      render(<SystemHealth />)

      await waitFor(() => {
        expect(screen.getByText('Performance Thresholds')).toBeInTheDocument()
      })
    })

    test('should show RPS thresholds', async () => {
      ;(api.fetchAdminStats as jest.Mock).mockResolvedValue(mockMetrics)

      render(<SystemHealth />)

      await waitFor(() => {
        expect(screen.getByText('?200: Excellent')).toBeInTheDocument()
        expect(screen.getByText('200-500: Good')).toBeInTheDocument()
        expect(screen.getByText('500-800: Warning')).toBeInTheDocument()
        expect(screen.getByText('>800: Critical')).toBeInTheDocument()
      })
    })
  })

  describe('Visual Indicators', () => {
    test('should show color dots for each metric', async () => {
      ;(api.fetchAdminStats as jest.Mock).mockResolvedValue(mockMetrics)

      const { container } = render(<SystemHealth />)

      await waitFor(() => {
        const dots = container.querySelectorAll('.w-2.h-2.rounded-full')
        // Should have dots for RPS, p99, cache, and queue
        expect(dots.length).toBeGreaterThanOrEqual(4)
      })
    })
  })

  describe('Accessibility', () => {
    test('should have proper heading structure', async () => {
      ;(api.fetchAdminStats as jest.Mock).mockResolvedValue(mockMetrics)

      render(<SystemHealth />)

      await waitFor(() => {
        const heading = screen.getByText(/System Health/)
        expect(heading.tagName).toBe('H2')
      })
    })
  })
})
