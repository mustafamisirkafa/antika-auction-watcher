/**
 * Tests for MetricsPanel component
 */

import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import MetricsPanel from '@/components/MetricsPanel'
import * as api from '@/lib/api'
import { SystemMetrics } from '@/types/metrics'

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

    return { data, error, isLoading }
  },
}))

// Mock API
jest.mock('@/lib/api')

describe('MetricsPanel Component', () => {
  const mockMetrics: SystemMetrics = {
    uptime: '5d 12h 42m',
    redis_hit_ratio: 0.92,
    requests_per_second: 135,
    response_time_ms: {
      p50: 110,
      p90: 160,
      p99: 230,
    },
    queue_pending: 14,
  }

  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('Loading State', () => {
    test('should show loading spinner', async () => {
      ;(api.fetchSystemMetrics as jest.Mock).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      )

      render(<MetricsPanel autoRefresh={false} />)

      expect(screen.getByText('Loading system metrics...')).toBeInTheDocument()
    })
  })

  describe('Error State', () => {
    test('should display error message when API fails', async () => {
      const errorMessage = 'Network error'
      ;(api.fetchSystemMetrics as jest.Mock).mockRejectedValue(
        new Error(errorMessage)
      )

      render(<MetricsPanel autoRefresh={false} />)

      await waitFor(() => {
        expect(screen.getByText('Failed to Load System Metrics')).toBeInTheDocument()
        expect(screen.getByText(errorMessage)).toBeInTheDocument()
      })
    })
  })

  describe('Data Display', () => {
    test('should display system uptime', async () => {
      ;(api.fetchSystemMetrics as jest.Mock).mockResolvedValue(mockMetrics)

      render(<MetricsPanel autoRefresh={false} />)

      await waitFor(() => {
        expect(screen.getByText('5d 12h 42m')).toBeInTheDocument()
      })
    })

    test('should display requests per second', async () => {
      ;(api.fetchSystemMetrics as jest.Mock).mockResolvedValue(mockMetrics)

      render(<MetricsPanel autoRefresh={false} />)

      await waitFor(() => {
        expect(screen.getByText('135')).toBeInTheDocument()
      })
    })

    test('should display queue pending', async () => {
      ;(api.fetchSystemMetrics as jest.Mock).mockResolvedValue(mockMetrics)

      render(<MetricsPanel autoRefresh={false} />)

      await waitFor(() => {
        expect(screen.getByText('14')).toBeInTheDocument()
      })
    })

    test('should display cache hit ratio', async () => {
      ;(api.fetchSystemMetrics as jest.Mock).mockResolvedValue(mockMetrics)

      render(<MetricsPanel autoRefresh={false} />)

      await waitFor(() => {
        expect(screen.getByText('92.0%')).toBeInTheDocument()
      })
    })

    test('should display response time percentiles', async () => {
      ;(api.fetchSystemMetrics as jest.Mock).mockResolvedValue(mockMetrics)

      render(<MetricsPanel autoRefresh={false} />)

      await waitFor(() => {
        expect(screen.getByText('110ms')).toBeInTheDocument()
        expect(screen.getByText('160ms')).toBeInTheDocument()
        expect(screen.getByText('230ms')).toBeInTheDocument()
      })
    })
  })

  describe('Color-Coded Indicators', () => {
    describe('Requests per Second', () => {
      test('should show green for normal load (?200)', async () => {
        ;(api.fetchSystemMetrics as jest.Mock).mockResolvedValue({
          ...mockMetrics,
          requests_per_second: 150,
        })

        const { container } = render(<MetricsPanel autoRefresh={false} />)

        await waitFor(() => {
          expect(screen.getByText('? Normal load')).toBeInTheDocument()
        })
      })

      test('should show blue for moderate load (200-500)', async () => {
        ;(api.fetchSystemMetrics as jest.Mock).mockResolvedValue({
          ...mockMetrics,
          requests_per_second: 350,
        })

        render(<MetricsPanel autoRefresh={false} />)

        await waitFor(() => {
          expect(screen.getByText('?? Moderate load')).toBeInTheDocument()
        })
      })

      test('should show yellow for high load (500-800)', async () => {
        ;(api.fetchSystemMetrics as jest.Mock).mockResolvedValue({
          ...mockMetrics,
          requests_per_second: 650,
        })

        render(<MetricsPanel autoRefresh={false} />)

        await waitFor(() => {
          expect(screen.getByText('?? High load')).toBeInTheDocument()
        })
      })

      test('should show red for critical load (>800)', async () => {
        ;(api.fetchSystemMetrics as jest.Mock).mockResolvedValue({
          ...mockMetrics,
          requests_per_second: 900,
        })

        render(<MetricsPanel autoRefresh={false} />)

        await waitFor(() => {
          expect(screen.getByText('?? Critical load')).toBeInTheDocument()
        })
      })
    })

    describe('Queue Pending', () => {
      test('should show green for healthy queue (?10)', async () => {
        ;(api.fetchSystemMetrics as jest.Mock).mockResolvedValue({
          ...mockMetrics,
          queue_pending: 5,
        })

        render(<MetricsPanel autoRefresh={false} />)

        await waitFor(() => {
          expect(screen.getByText('? Queue healthy')).toBeInTheDocument()
        })
      })

      test('should show blue for moderate queue (10-50)', async () => {
        ;(api.fetchSystemMetrics as jest.Mock).mockResolvedValue({
          ...mockMetrics,
          queue_pending: 30,
        })

        render(<MetricsPanel autoRefresh={false} />)

        await waitFor(() => {
          expect(screen.getByText('?? Moderate queue')).toBeInTheDocument()
        })
      })

      test('should show yellow for building queue (50-100)', async () => {
        ;(api.fetchSystemMetrics as jest.Mock).mockResolvedValue({
          ...mockMetrics,
          queue_pending: 75,
        })

        render(<MetricsPanel autoRefresh={false} />)

        await waitFor(() => {
          expect(screen.getByText('?? Queue building')).toBeInTheDocument()
        })
      })

      test('should show red for critical queue (>100)', async () => {
        ;(api.fetchSystemMetrics as jest.Mock).mockResolvedValue({
          ...mockMetrics,
          queue_pending: 150,
        })

        render(<MetricsPanel autoRefresh={false} />)

        await waitFor(() => {
          expect(screen.getByText('?? Queue critical')).toBeInTheDocument()
        })
      })
    })

    describe('Cache Hit Ratio', () => {
      test('should show green for excellent caching (?90%)', async () => {
        ;(api.fetchSystemMetrics as jest.Mock).mockResolvedValue({
          ...mockMetrics,
          redis_hit_ratio: 0.95,
        })

        render(<MetricsPanel autoRefresh={false} />)

        await waitFor(() => {
          expect(screen.getByText('? Excellent caching')).toBeInTheDocument()
        })
      })

      test('should show blue for good caching (75-90%)', async () => {
        ;(api.fetchSystemMetrics as jest.Mock).mockResolvedValue({
          ...mockMetrics,
          redis_hit_ratio: 0.82,
        })

        render(<MetricsPanel autoRefresh={false} />)

        await waitFor(() => {
          expect(screen.getByText('?? Good caching')).toBeInTheDocument()
        })
      })

      test('should show yellow for warming cache (60-75%)', async () => {
        ;(api.fetchSystemMetrics as jest.Mock).mockResolvedValue({
          ...mockMetrics,
          redis_hit_ratio: 0.68,
        })

        render(<MetricsPanel autoRefresh={false} />)

        await waitFor(() => {
          expect(screen.getByText('?? Cache warming')).toBeInTheDocument()
        })
      })

      test('should show red for cache issues (<60%)', async () => {
        ;(api.fetchSystemMetrics as jest.Mock).mockResolvedValue({
          ...mockMetrics,
          redis_hit_ratio: 0.45,
        })

        render(<MetricsPanel autoRefresh={false} />)

        await waitFor(() => {
          expect(screen.getByText('?? Cache issues')).toBeInTheDocument()
        })
      })
    })
  })

  describe('Charts Rendering', () => {
    test('should render response time distribution chart', async () => {
      ;(api.fetchSystemMetrics as jest.Mock).mockResolvedValue(mockMetrics)

      render(<MetricsPanel autoRefresh={false} />)

      await waitFor(() => {
        expect(screen.getByText('Response Time Distribution')).toBeInTheDocument()
      })
    })

    test('should render cache performance radial chart', async () => {
      ;(api.fetchSystemMetrics as jest.Mock).mockResolvedValue(mockMetrics)

      render(<MetricsPanel autoRefresh={false} />)

      await waitFor(() => {
        expect(screen.getByText('Redis Cache Performance')).toBeInTheDocument()
      })
    })
  })

  describe('Performance Thresholds Legend', () => {
    test('should display performance thresholds', async () => {
      ;(api.fetchSystemMetrics as jest.Mock).mockResolvedValue(mockMetrics)

      render(<MetricsPanel autoRefresh={false} />)

      await waitFor(() => {
        expect(screen.getByText('Performance Thresholds')).toBeInTheDocument()
      })
    })

    test('should show response time thresholds', async () => {
      ;(api.fetchSystemMetrics as jest.Mock).mockResolvedValue(mockMetrics)

      render(<MetricsPanel autoRefresh={false} />)

      await waitFor(() => {
        expect(screen.getByText('<200ms: Excellent')).toBeInTheDocument()
        expect(screen.getByText('200-400ms: Good')).toBeInTheDocument()
        expect(screen.getByText('400-800ms: Warning')).toBeInTheDocument()
        expect(screen.getByText('>800ms: Critical')).toBeInTheDocument()
      })
    })

    test('should show cache hit ratio thresholds', async () => {
      ;(api.fetchSystemMetrics as jest.Mock).mockResolvedValue(mockMetrics)

      render(<MetricsPanel autoRefresh={false} />)

      await waitFor(() => {
        expect(screen.getByText('?90%: Excellent')).toBeInTheDocument()
        expect(screen.getByText('75-90%: Good')).toBeInTheDocument()
        expect(screen.getByText('60-75%: Warning')).toBeInTheDocument()
        expect(screen.getByText('<60%: Critical')).toBeInTheDocument()
      })
    })
  })

  describe('Auto-refresh', () => {
    test('should show auto-refresh indicator when enabled', async () => {
      ;(api.fetchSystemMetrics as jest.Mock).mockResolvedValue(mockMetrics)

      render(<MetricsPanel autoRefresh={true} refreshInterval={60000} />)

      await waitFor(() => {
        expect(screen.getByText(/Auto-refresh: 60s/)).toBeInTheDocument()
      })
    })

    test('should not show auto-refresh indicator when disabled', async () => {
      ;(api.fetchSystemMetrics as jest.Mock).mockResolvedValue(mockMetrics)

      render(<MetricsPanel autoRefresh={false} />)

      await waitFor(() => {
        expect(screen.queryByText(/Auto-refresh/)).not.toBeInTheDocument()
      })
    })
  })

  describe('System Health Summary', () => {
    test('should display comprehensive system summary', async () => {
      ;(api.fetchSystemMetrics as jest.Mock).mockResolvedValue(mockMetrics)

      render(<MetricsPanel autoRefresh={false} />)

      await waitFor(() => {
        expect(screen.getByText('System Health Summary')).toBeInTheDocument()
        const summary = screen.getByText(/System has been running/)
        expect(summary).toHaveTextContent('5d 12h 42m')
        expect(summary).toHaveTextContent('135')
        expect(summary).toHaveTextContent('230ms')
        expect(summary).toHaveTextContent('92.0%')
        expect(summary).toHaveTextContent('14')
      })
    })
  })

  describe('Cache Hit/Miss Display', () => {
    test('should calculate and display cache hit percentage', async () => {
      ;(api.fetchSystemMetrics as jest.Mock).mockResolvedValue({
        ...mockMetrics,
        redis_hit_ratio: 0.85,
      })

      render(<MetricsPanel autoRefresh={false} />)

      await waitFor(() => {
        expect(screen.getByText('~85%')).toBeInTheDocument()
      })
    })

    test('should calculate and display cache miss percentage', async () => {
      ;(api.fetchSystemMetrics as jest.Mock).mockResolvedValue({
        ...mockMetrics,
        redis_hit_ratio: 0.85,
      })

      render(<MetricsPanel autoRefresh={false} />)

      await waitFor(() => {
        expect(screen.getByText('~15%')).toBeInTheDocument()
      })
    })
  })

  describe('Live Indicator', () => {
    test('should show live status indicator', async () => {
      ;(api.fetchSystemMetrics as jest.Mock).mockResolvedValue(mockMetrics)

      render(<MetricsPanel autoRefresh={false} />)

      await waitFor(() => {
        expect(screen.getByText('Live')).toBeInTheDocument()
      })
    })
  })

  describe('Data Formatting', () => {
    test('should format percentages to 1 decimal place', async () => {
      ;(api.fetchSystemMetrics as jest.Mock).mockResolvedValue({
        ...mockMetrics,
        redis_hit_ratio: 0.92567,
      })

      render(<MetricsPanel autoRefresh={false} />)

      await waitFor(() => {
        expect(screen.getByText('92.6%')).toBeInTheDocument()
      })
    })
  })

  describe('Responsive Bar Colors', () => {
    test('should use appropriate colors for response time bars', async () => {
      ;(api.fetchSystemMetrics as jest.Mock).mockResolvedValue({
        ...mockMetrics,
        response_time_ms: {
          p50: 150,  // Green (excellent)
          p90: 350,  // Blue (good)
          p99: 750,  // Yellow (warning)
        },
      })

      const { container } = render(<MetricsPanel autoRefresh={false} />)

      await waitFor(() => {
        // Check for green bar (p50 < 200ms)
        const greenBars = container.querySelectorAll('rect[fill="#10b981"]')
        expect(greenBars.length).toBeGreaterThan(0)
      })
    })
  })

  describe('Accessibility', () => {
    test('should have proper heading structure', async () => {
      ;(api.fetchSystemMetrics as jest.Mock).mockResolvedValue(mockMetrics)

      render(<MetricsPanel autoRefresh={false} />)

      await waitFor(() => {
        const heading = screen.getByText(/System Metrics/)
        expect(heading.tagName).toBe('H2')
      })
    })

    test('should have descriptive chart titles', async () => {
      ;(api.fetchSystemMetrics as jest.Mock).mockResolvedValue(mockMetrics)

      render(<MetricsPanel autoRefresh={false} />)

      await waitFor(() => {
        expect(screen.getByText('Response Time Distribution')).toBeInTheDocument()
        expect(screen.getByText('Redis Cache Performance')).toBeInTheDocument()
      })
    })
  })

  describe('Edge Cases', () => {
    test('should handle zero requests per second', async () => {
      ;(api.fetchSystemMetrics as jest.Mock).mockResolvedValue({
        ...mockMetrics,
        requests_per_second: 0,
      })

      render(<MetricsPanel autoRefresh={false} />)

      await waitFor(() => {
        expect(screen.getByText('0')).toBeInTheDocument()
      })
    })

    test('should handle 100% cache hit ratio', async () => {
      ;(api.fetchSystemMetrics as jest.Mock).mockResolvedValue({
        ...mockMetrics,
        redis_hit_ratio: 1.0,
      })

      render(<MetricsPanel autoRefresh={false} />)

      await waitFor(() => {
        expect(screen.getByText('100.0%')).toBeInTheDocument()
      })
    })

    test('should handle 0% cache hit ratio', async () => {
      ;(api.fetchSystemMetrics as jest.Mock).mockResolvedValue({
        ...mockMetrics,
        redis_hit_ratio: 0.0,
      })

      render(<MetricsPanel autoRefresh={false} />)

      await waitFor(() => {
        expect(screen.getByText('0.0%')).toBeInTheDocument()
      })
    })
  })
})
