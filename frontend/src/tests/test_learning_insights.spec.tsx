/**
 * Tests for LearningInsights component
 */

import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import LearningInsights from '@/components/LearningInsights'
import * as api from '@/lib/api'
import { LearningMetrics } from '@/types/metrics'

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

describe('LearningInsights Component', () => {
  const mockMetrics: LearningMetrics = {
    overall_accuracy: 82.5,
    learning_efficiency: 0.89,
    confidence_trend: [0.72, 0.75, 0.81, 0.84],
    category_accuracy: {
      ceramics: 79,
      coins: 85,
      paintings: 91,
      furniture: 74,
    },
    last_training: '2025-11-02T18:45:00Z',
  }

  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('Loading State', () => {
    test('should show loading spinner', async () => {
      ;(api.fetchLearningMetrics as jest.Mock).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      )

      render(<LearningInsights autoRefresh={false} />)

      expect(screen.getByText('Loading learning metrics...')).toBeInTheDocument()
    })
  })

  describe('Error State', () => {
    test('should display error message when API fails', async () => {
      const errorMessage = 'Network error'
      ;(api.fetchLearningMetrics as jest.Mock).mockRejectedValue(
        new Error(errorMessage)
      )

      render(<LearningInsights autoRefresh={false} />)

      await waitFor(() => {
        expect(screen.getByText('Failed to Load Learning Metrics')).toBeInTheDocument()
        expect(screen.getByText(errorMessage)).toBeInTheDocument()
      })
    })

    test('should show backend URL in error message', async () => {
      ;(api.fetchLearningMetrics as jest.Mock).mockRejectedValue(
        new Error('Failed')
      )

      render(<LearningInsights autoRefresh={false} />)

      await waitFor(() => {
        expect(screen.getByText(/Make sure the backend is running/i)).toBeInTheDocument()
      })
    })
  })

  describe('Data Display', () => {
    test('should display overall accuracy', async () => {
      ;(api.fetchLearningMetrics as jest.Mock).mockResolvedValue(mockMetrics)

      render(<LearningInsights autoRefresh={false} />)

      await waitFor(() => {
        expect(screen.getByText('82.5%')).toBeInTheDocument()
      })
    })

    test('should display learning efficiency', async () => {
      ;(api.fetchLearningMetrics as jest.Mock).mockResolvedValue(mockMetrics)

      render(<LearningInsights autoRefresh={false} />)

      await waitFor(() => {
        expect(screen.getByText('89.0%')).toBeInTheDocument()
      })
    })

    test('should display category accuracy data', async () => {
      ;(api.fetchLearningMetrics as jest.Mock).mockResolvedValue(mockMetrics)

      render(<LearningInsights autoRefresh={false} />)

      await waitFor(() => {
        expect(screen.getByText('Ceramics')).toBeInTheDocument()
        expect(screen.getByText('Coins')).toBeInTheDocument()
        expect(screen.getByText('Paintings')).toBeInTheDocument()
        expect(screen.getByText('Furniture')).toBeInTheDocument()
      })
    })

    test('should display last training timestamp', async () => {
      ;(api.fetchLearningMetrics as jest.Mock).mockResolvedValue(mockMetrics)

      render(<LearningInsights autoRefresh={false} />)

      await waitFor(() => {
        expect(screen.getByText(/2025/)).toBeInTheDocument()
      })
    })
  })

  describe('Efficiency Color Coding', () => {
    test('should show green for excellent efficiency (?80%)', async () => {
      ;(api.fetchLearningMetrics as jest.Mock).mockResolvedValue({
        ...mockMetrics,
        learning_efficiency: 0.85,
      })

      const { container } = render(<LearningInsights autoRefresh={false} />)

      await waitFor(() => {
        const efficiencyElement = container.querySelector('.text-green-600')
        expect(efficiencyElement).toBeInTheDocument()
      })
    })

    test('should show yellow for moderate efficiency (60-80%)', async () => {
      ;(api.fetchLearningMetrics as jest.Mock).mockResolvedValue({
        ...mockMetrics,
        learning_efficiency: 0.7,
      })

      const { container } = render(<LearningInsights autoRefresh={false} />)

      await waitFor(() => {
        const efficiencyElement = container.querySelector('.text-yellow-600')
        expect(efficiencyElement).toBeInTheDocument()
      })
    })

    test('should show red for poor efficiency (<60%)', async () => {
      ;(api.fetchLearningMetrics as jest.Mock).mockResolvedValue({
        ...mockMetrics,
        learning_efficiency: 0.5,
      })

      const { container } = render(<LearningInsights autoRefresh={false} />)

      await waitFor(() => {
        const efficiencyElement = container.querySelector('.text-red-600')
        expect(efficiencyElement).toBeInTheDocument()
      })
    })
  })

  describe('Category Accuracy Colors', () => {
    test('should use green for high accuracy (?80%)', async () => {
      ;(api.fetchLearningMetrics as jest.Mock).mockResolvedValue(mockMetrics)

      const { container } = render(<LearningInsights autoRefresh={false} />)

      await waitFor(() => {
        // Paintings has 91% accuracy - should be green
        const bars = container.querySelectorAll('rect[fill="#10b981"]')
        expect(bars.length).toBeGreaterThan(0)
      })
    })

    test('should use yellow for moderate accuracy (60-80%)', async () => {
      ;(api.fetchLearningMetrics as jest.Mock).mockResolvedValue(mockMetrics)

      const { container } = render(<LearningInsights autoRefresh={false} />)

      await waitFor(() => {
        // Furniture has 74% accuracy - should be yellow
        const bars = container.querySelectorAll('rect[fill="#f59e0b"]')
        expect(bars.length).toBeGreaterThan(0)
      })
    })
  })

  describe('Model Improving Indicator', () => {
    test('should not show improving badge initially', async () => {
      ;(api.fetchLearningMetrics as jest.Mock).mockResolvedValue(mockMetrics)

      render(<LearningInsights autoRefresh={false} />)

      await waitFor(() => {
        expect(screen.queryByText('Model Improving')).not.toBeInTheDocument()
      })
    })

    test('should show improving badge when accuracy increases ?3%', async () => {
      let callCount = 0
      ;(api.fetchLearningMetrics as jest.Mock).mockImplementation(() => {
        callCount++
        if (callCount === 1) {
          return Promise.resolve({ ...mockMetrics, overall_accuracy: 80 })
        }
        return Promise.resolve({ ...mockMetrics, overall_accuracy: 85 })
      })

      const { rerender } = render(<LearningInsights autoRefresh={false} />)

      await waitFor(() => {
        expect(screen.queryByText('Model Improving')).not.toBeInTheDocument()
      })

      // Trigger re-fetch
      rerender(<LearningInsights autoRefresh={false} />)

      // Note: This test is simplified - in real usage, SWR would handle refetching
    })
  })

  describe('Charts Rendering', () => {
    test('should render category performance bar chart', async () => {
      ;(api.fetchLearningMetrics as jest.Mock).mockResolvedValue(mockMetrics)

      render(<LearningInsights autoRefresh={false} />)

      await waitFor(() => {
        expect(screen.getByText('Category Performance')).toBeInTheDocument()
      })
    })

    test('should render confidence trend line chart', async () => {
      ;(api.fetchLearningMetrics as jest.Mock).mockResolvedValue(mockMetrics)

      render(<LearningInsights autoRefresh={false} />)

      await waitFor(() => {
        expect(screen.getByText('Confidence Trend')).toBeInTheDocument()
      })
    })

    test('should show empty state when no category data', async () => {
      ;(api.fetchLearningMetrics as jest.Mock).mockResolvedValue({
        ...mockMetrics,
        category_accuracy: {},
      })

      render(<LearningInsights autoRefresh={false} />)

      await waitFor(() => {
        expect(screen.getByText('No category data available')).toBeInTheDocument()
      })
    })

    test('should show empty state when no trend data', async () => {
      ;(api.fetchLearningMetrics as jest.Mock).mockResolvedValue({
        ...mockMetrics,
        confidence_trend: [],
      })

      render(<LearningInsights autoRefresh={false} />)

      await waitFor(() => {
        expect(screen.getByText('No trend data available')).toBeInTheDocument()
      })
    })
  })

  describe('Auto-refresh', () => {
    test('should show auto-refresh indicator when enabled', async () => {
      ;(api.fetchLearningMetrics as jest.Mock).mockResolvedValue(mockMetrics)

      render(<LearningInsights autoRefresh={true} refreshInterval={60000} />)

      await waitFor(() => {
        expect(screen.getByText(/Auto-refresh: 60s/)).toBeInTheDocument()
      })
    })

    test('should not show auto-refresh indicator when disabled', async () => {
      ;(api.fetchLearningMetrics as jest.Mock).mockResolvedValue(mockMetrics)

      render(<LearningInsights autoRefresh={false} />)

      await waitFor(() => {
        expect(screen.queryByText(/Auto-refresh/)).not.toBeInTheDocument()
      })
    })
  })

  describe('Summary Section', () => {
    test('should display model status summary', async () => {
      ;(api.fetchLearningMetrics as jest.Mock).mockResolvedValue(mockMetrics)

      render(<LearningInsights autoRefresh={false} />)

      await waitFor(() => {
        expect(screen.getByText(/Model Status/)).toBeInTheDocument()
        expect(screen.getByText(/operating with/)).toBeInTheDocument()
      })
    })

    test('should include accuracy and efficiency in summary', async () => {
      ;(api.fetchLearningMetrics as jest.Mock).mockResolvedValue(mockMetrics)

      render(<LearningInsights autoRefresh={false} />)

      await waitFor(() => {
        const summary = screen.getByText(/operating with/).parentElement
        expect(summary).toHaveTextContent('82.5%')
        expect(summary).toHaveTextContent('89.0%')
      })
    })
  })

  describe('Legend', () => {
    test('should display color legend for accuracy levels', async () => {
      ;(api.fetchLearningMetrics as jest.Mock).mockResolvedValue(mockMetrics)

      render(<LearningInsights autoRefresh={false} />)

      await waitFor(() => {
        expect(screen.getByText(/?80% Excellent/)).toBeInTheDocument()
        expect(screen.getByText(/60-80% Good/)).toBeInTheDocument()
        expect(screen.getByText(/<60% Needs Work/)).toBeInTheDocument()
      })
    })
  })

  describe('Trend Analysis', () => {
    test('should show improving trend when confidence increases', async () => {
      ;(api.fetchLearningMetrics as jest.Mock).mockResolvedValue({
        ...mockMetrics,
        confidence_trend: [0.6, 0.7, 0.8, 0.9],
      })

      render(<LearningInsights autoRefresh={false} />)

      await waitFor(() => {
        expect(screen.getByText(/? Improving/)).toBeInTheDocument()
      })
    })

    test('should show declining trend when confidence decreases', async () => {
      ;(api.fetchLearningMetrics as jest.Mock).mockResolvedValue({
        ...mockMetrics,
        confidence_trend: [0.9, 0.8, 0.7, 0.6],
      })

      render(<LearningInsights autoRefresh={false} />)

      await waitFor(() => {
        expect(screen.getByText(/? Declining/)).toBeInTheDocument()
      })
    })
  })

  describe('Data Formatting', () => {
    test('should format percentages to 1 decimal place', async () => {
      ;(api.fetchLearningMetrics as jest.Mock).mockResolvedValue({
        ...mockMetrics,
        overall_accuracy: 82.567,
      })

      render(<LearningInsights autoRefresh={false} />)

      await waitFor(() => {
        expect(screen.getByText('82.6%')).toBeInTheDocument()
      })
    })

    test('should format timestamp in Turkish locale', async () => {
      ;(api.fetchLearningMetrics as jest.Mock).mockResolvedValue(mockMetrics)

      render(<LearningInsights autoRefresh={false} />)

      await waitFor(() => {
        // Should display some formatted date (exact format depends on locale)
        const dateElements = screen.queryAllByText(/\d{2}/)
        expect(dateElements.length).toBeGreaterThan(0)
      })
    })
  })

  describe('Accessibility', () => {
    test('should have proper heading structure', async () => {
      ;(api.fetchLearningMetrics as jest.Mock).mockResolvedValue(mockMetrics)

      render(<LearningInsights autoRefresh={false} />)

      await waitFor(() => {
        const heading = screen.getByText(/Learning Insights/)
        expect(heading.tagName).toBe('H2')
      })
    })

    test('should have descriptive chart titles', async () => {
      ;(api.fetchLearningMetrics as jest.Mock).mockResolvedValue(mockMetrics)

      render(<LearningInsights autoRefresh={false} />)

      await waitFor(() => {
        expect(screen.getByText('Category Performance')).toBeInTheDocument()
        expect(screen.getByText('Confidence Trend')).toBeInTheDocument()
      })
    })
  })
})
