/**
 * Tests for LearningLogs component - pagination and search
 */

import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import LearningLogs from '@/components/LearningLogs'
import * as api from '@/lib/api'
import { LearningLogEntry } from '@/types/admin'

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

describe('LearningLogs Component', () => {
  const mockLogs: LearningLogEntry[] = Array.from({ length: 25 }, (_, i) => ({
    timestamp: `2025-11-${(i % 30) + 1 < 10 ? '0' : ''}${(i % 30) + 1}T10:00:00Z`,
    category: ['antiques', 'ceramics', 'coins', 'paintings'][i % 4],
    samples: 50 + i * 5,
    accuracy_before: 70 + (i % 15),
    accuracy_after: 75 + (i % 15),
    notes: i % 3 === 0 ? `Training note ${i}` : undefined,
  }))

  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('Loading State', () => {
    test('should show loading spinner', () => {
      ;(api.fetchLearningHistory as jest.Mock).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      )

      render(<LearningLogs />)

      expect(screen.getByText('Loading learning logs...')).toBeInTheDocument()
    })
  })

  describe('Error State', () => {
    test('should display error message when API fails', async () => {
      ;(api.fetchLearningHistory as jest.Mock).mockRejectedValue(
        new Error('Network error')
      )

      render(<LearningLogs />)

      await waitFor(() => {
        expect(screen.getByText('Failed to Load Learning Logs')).toBeInTheDocument()
        expect(screen.getByText('Network error')).toBeInTheDocument()
      })
    })
  })

  describe('Data Display', () => {
    test('should display learning logs in table', async () => {
      ;(api.fetchLearningHistory as jest.Mock).mockResolvedValue({
        logs: mockLogs.slice(0, 5),
        total: 5,
      })

      render(<LearningLogs />)

      await waitFor(() => {
        expect(screen.getByText('antiques')).toBeInTheDocument()
        expect(screen.getByText('ceramics')).toBeInTheDocument()
      })
    })

    test('should display all table columns', async () => {
      ;(api.fetchLearningHistory as jest.Mock).mockResolvedValue({
        logs: mockLogs.slice(0, 1),
        total: 1,
      })

      render(<LearningLogs />)

      await waitFor(() => {
        expect(screen.getByText('Timestamp')).toBeInTheDocument()
        expect(screen.getByText('Category')).toBeInTheDocument()
        expect(screen.getByText('Samples')).toBeInTheDocument()
        expect(screen.getByText('Accuracy Before')).toBeInTheDocument()
        expect(screen.getByText('Accuracy After')).toBeInTheDocument()
        expect(screen.getByText('Change')).toBeInTheDocument()
        expect(screen.getByText('Notes')).toBeInTheDocument()
      })
    })

    test('should show empty state when no logs', async () => {
      ;(api.fetchLearningHistory as jest.Mock).mockResolvedValue({
        logs: [],
        total: 0,
      })

      render(<LearningLogs />)

      await waitFor(() => {
        expect(screen.getByText('No Logs Found')).toBeInTheDocument()
        expect(screen.getByText('No training logs available yet')).toBeInTheDocument()
      })
    })
  })

  describe('Search Functionality', () => {
    test('should filter logs by category', async () => {
      ;(api.fetchLearningHistory as jest.Mock).mockResolvedValue({
        logs: mockLogs,
        total: mockLogs.length,
      })

      render(<LearningLogs />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Search by category...')).toBeInTheDocument()
      })

      // Search for "antiques"
      const searchInput = screen.getByPlaceholderText('Search by category...')
      fireEvent.change(searchInput, { target: { value: 'antiques' } })

      await waitFor(() => {
        // Should only show antiques entries
        const categoryBadges = screen.getAllByText('antiques')
        expect(categoryBadges.length).toBeGreaterThan(0)
        
        // Should not show other categories
        expect(screen.queryByText('ceramics')).not.toBeInTheDocument()
      })
    })

    test('should be case-insensitive', async () => {
      ;(api.fetchLearningHistory as jest.Mock).mockResolvedValue({
        logs: mockLogs,
        total: mockLogs.length,
      })

      render(<LearningLogs />)

      await waitFor(() => {
        const searchInput = screen.getByPlaceholderText('Search by category...')
        fireEvent.change(searchInput, { target: { value: 'ANTIQUES' } })
      })

      await waitFor(() => {
        expect(screen.getByText('antiques')).toBeInTheDocument()
      })
    })

    test('should show clear button when search has value', async () => {
      ;(api.fetchLearningHistory as jest.Mock).mockResolvedValue({
        logs: mockLogs,
        total: mockLogs.length,
      })

      render(<LearningLogs />)

      const searchInput = screen.getByPlaceholderText('Search by category...')
      fireEvent.change(searchInput, { target: { value: 'antiques' } })

      await waitFor(() => {
        const clearButton = searchInput.parentElement?.querySelector('button')
        expect(clearButton).toBeInTheDocument()
      })
    })

    test('should clear search when clear button clicked', async () => {
      ;(api.fetchLearningHistory as jest.Mock).mockResolvedValue({
        logs: mockLogs,
        total: mockLogs.length,
      })

      render(<LearningLogs />)

      const searchInput = screen.getByPlaceholderText('Search by category...') as HTMLInputElement
      fireEvent.change(searchInput, { target: { value: 'antiques' } })

      await waitFor(() => {
        expect(searchInput.value).toBe('antiques')
      })

      const clearButton = searchInput.parentElement?.querySelector('button')
      if (clearButton) {
        fireEvent.click(clearButton)
      }

      await waitFor(() => {
        expect(searchInput.value).toBe('')
      })
    })

    test('should reset to page 1 when search changes', async () => {
      ;(api.fetchLearningHistory as jest.Mock).mockResolvedValue({
        logs: mockLogs,
        total: mockLogs.length,
      })

      render(<LearningLogs />)

      await waitFor(() => {
        // Go to page 2
        const nextButton = screen.getByText('Next')
        fireEvent.click(nextButton)
      })

      // Now search - should reset to page 1
      const searchInput = screen.getByPlaceholderText('Search by category...')
      fireEvent.change(searchInput, { target: { value: 'coins' } })

      await waitFor(() => {
        expect(screen.getByText(/Page 1/)).toBeInTheDocument()
      })
    })

    test('should show filtered count', async () => {
      ;(api.fetchLearningHistory as jest.Mock).mockResolvedValue({
        logs: mockLogs,
        total: mockLogs.length,
      })

      render(<LearningLogs />)

      const searchInput = screen.getByPlaceholderText('Search by category...')
      fireEvent.change(searchInput, { target: { value: 'antiques' } })

      await waitFor(() => {
        expect(screen.getByText(/filtered by "antiques"/)).toBeInTheDocument()
      })
    })
  })

  describe('Pagination', () => {
    test('should paginate logs (10 items per page)', async () => {
      ;(api.fetchLearningHistory as jest.Mock).mockResolvedValue({
        logs: mockLogs,
        total: mockLogs.length,
      })

      render(<LearningLogs />)

      await waitFor(() => {
        const rows = screen.getAllByRole('row')
        // Header + 10 data rows
        expect(rows.length).toBe(11)
      })
    })

    test('should show pagination controls when needed', async () => {
      ;(api.fetchLearningHistory as jest.Mock).mockResolvedValue({
        logs: mockLogs,
        total: mockLogs.length,
      })

      render(<LearningLogs />)

      await waitFor(() => {
        expect(screen.getByText('First')).toBeInTheDocument()
        expect(screen.getByText('Previous')).toBeInTheDocument()
        expect(screen.getByText('Next')).toBeInTheDocument()
        expect(screen.getByText('Last')).toBeInTheDocument()
      })
    })

    test('should disable First and Previous on page 1', async () => {
      ;(api.fetchLearningHistory as jest.Mock).mockResolvedValue({
        logs: mockLogs,
        total: mockLogs.length,
      })

      render(<LearningLogs />)

      await waitFor(() => {
        const firstButton = screen.getByText('First') as HTMLButtonElement
        const prevButton = screen.getByText('Previous') as HTMLButtonElement
        
        expect(firstButton.disabled).toBe(true)
        expect(prevButton.disabled).toBe(true)
      })
    })

    test('should navigate to next page', async () => {
      ;(api.fetchLearningHistory as jest.Mock).mockResolvedValue({
        logs: mockLogs,
        total: mockLogs.length,
      })

      render(<LearningLogs />)

      await waitFor(() => {
        expect(screen.getByText('Page 1 of 3')).toBeInTheDocument()
      })

      const nextButton = screen.getByText('Next')
      fireEvent.click(nextButton)

      await waitFor(() => {
        expect(screen.getByText('Page 2 of 3')).toBeInTheDocument()
      })
    })

    test('should navigate to last page', async () => {
      ;(api.fetchLearningHistory as jest.Mock).mockResolvedValue({
        logs: mockLogs,
        total: mockLogs.length,
      })

      render(<LearningLogs />)

      const lastButton = screen.getByText('Last')
      fireEvent.click(lastButton)

      await waitFor(() => {
        expect(screen.getByText('Page 3 of 3')).toBeInTheDocument()
      })
    })

    test('should disable Next and Last on last page', async () => {
      ;(api.fetchLearningHistory as jest.Mock).mockResolvedValue({
        logs: mockLogs,
        total: mockLogs.length,
      })

      render(<LearningLogs />)

      // Go to last page
      const lastButton = screen.getByText('Last')
      fireEvent.click(lastButton)

      await waitFor(() => {
        const nextButton = screen.getByText('Next') as HTMLButtonElement
        const lastBtn = screen.getByText('Last') as HTMLButtonElement
        
        expect(nextButton.disabled).toBe(true)
        expect(lastBtn.disabled).toBe(true)
      })
    })

    test('should show page numbers', async () => {
      ;(api.fetchLearningHistory as jest.Mock).mockResolvedValue({
        logs: mockLogs,
        total: mockLogs.length,
      })

      render(<LearningLogs />)

      await waitFor(() => {
        expect(screen.getByText('1')).toBeInTheDocument()
        expect(screen.getByText('2')).toBeInTheDocument()
        expect(screen.getByText('3')).toBeInTheDocument()
      })
    })

    test('should highlight current page number', async () => {
      ;(api.fetchLearningHistory as jest.Mock).mockResolvedValue({
        logs: mockLogs,
        total: mockLogs.length,
      })

      render(<LearningLogs />)

      await waitFor(() => {
        const pageButton = screen.getByText('1').closest('button')
        expect(pageButton).toHaveClass('bg-primary-600')
      })
    })
  })

  describe('Accuracy Change Display', () => {
    test('should show positive change in green with up arrow', async () => {
      const logs: LearningLogEntry[] = [
        {
          timestamp: '2025-11-02T10:00:00Z',
          category: 'antiques',
          samples: 50,
          accuracy_before: 70,
          accuracy_after: 85,
          notes: 'Improvement',
        },
      ]

      ;(api.fetchLearningHistory as jest.Mock).mockResolvedValue({
        logs,
        total: 1,
      })

      render(<LearningLogs />)

      await waitFor(() => {
        expect(screen.getByText(/?/)).toBeInTheDocument()
        const changeElement = screen.getByText(/?/).parentElement
        expect(changeElement).toHaveClass('text-green-600')
      })
    })

    test('should show negative change in red with down arrow', async () => {
      const logs: LearningLogEntry[] = [
        {
          timestamp: '2025-11-02T10:00:00Z',
          category: 'ceramics',
          samples: 50,
          accuracy_before: 85,
          accuracy_after: 75,
        },
      ]

      ;(api.fetchLearningHistory as jest.Mock).mockResolvedValue({
        logs,
        total: 1,
      })

      render(<LearningLogs />)

      await waitFor(() => {
        expect(screen.getByText(/?/)).toBeInTheDocument()
        const changeElement = screen.getByText(/?/).parentElement
        expect(changeElement).toHaveClass('text-red-600')
      })
    })

    test('should show no change in gray with arrow', async () => {
      const logs: LearningLogEntry[] = [
        {
          timestamp: '2025-11-02T10:00:00Z',
          category: 'coins',
          samples: 50,
          accuracy_before: 80,
          accuracy_after: 80,
        },
      ]

      ;(api.fetchLearningHistory as jest.Mock).mockResolvedValue({
        logs,
        total: 1,
      })

      render(<LearningLogs />)

      await waitFor(() => {
        expect(screen.getByText(/?/)).toBeInTheDocument()
      })
    })
  })

  describe('Notes Display', () => {
    test('should display notes when available', async () => {
      const logs: LearningLogEntry[] = [
        {
          timestamp: '2025-11-02T10:00:00Z',
          category: 'antiques',
          samples: 50,
          accuracy_before: 70,
          accuracy_after: 75,
          notes: 'Important training note',
        },
      ]

      ;(api.fetchLearningHistory as jest.Mock).mockResolvedValue({
        logs,
        total: 1,
      })

      render(<LearningLogs />)

      await waitFor(() => {
        expect(screen.getByText('Important training note')).toBeInTheDocument()
      })
    })

    test('should show dash when notes missing', async () => {
      const logs: LearningLogEntry[] = [
        {
          timestamp: '2025-11-02T10:00:00Z',
          category: 'antiques',
          samples: 50,
          accuracy_before: 70,
          accuracy_after: 75,
        },
      ]

      ;(api.fetchLearningHistory as jest.Mock).mockResolvedValue({
        logs,
        total: 1,
      })

      render(<LearningLogs />)

      await waitFor(() => {
        // Check for dash in notes column
        const cells = screen.getAllByRole('cell')
        const notesCell = cells[cells.length - 1] // Last cell should be notes
        expect(notesCell).toHaveTextContent('-')
      })
    })
  })

  describe('Results Count', () => {
    test('should show total count', async () => {
      ;(api.fetchLearningHistory as jest.Mock).mockResolvedValue({
        logs: mockLogs,
        total: mockLogs.length,
      })

      render(<LearningLogs />)

      await waitFor(() => {
        expect(screen.getByText(/Showing \d+ of 25 entries/)).toBeInTheDocument()
      })
    })

    test('should show filtered count when searching', async () => {
      ;(api.fetchLearningHistory as jest.Mock).mockResolvedValue({
        logs: mockLogs,
        total: mockLogs.length,
      })

      render(<LearningLogs />)

      const searchInput = screen.getByPlaceholderText('Search by category...')
      fireEvent.change(searchInput, { target: { value: 'antiques' } })

      await waitFor(() => {
        expect(screen.getByText(/Showing \d+ of \d+ entries \(filtered by "antiques"\)/)).toBeInTheDocument()
      })
    })
  })

  describe('Category Badge Styling', () => {
    test('should display categories with badge styling', async () => {
      const logs: LearningLogEntry[] = [
        {
          timestamp: '2025-11-02T10:00:00Z',
          category: 'antiques',
          samples: 50,
          accuracy_before: 70,
          accuracy_after: 75,
        },
      ]

      ;(api.fetchLearningHistory as jest.Mock).mockResolvedValue({
        logs,
        total: 1,
      })

      const { container } = render(<LearningLogs />)

      await waitFor(() => {
        const badge = container.querySelector('.bg-blue-100.text-blue-800')
        expect(badge).toBeInTheDocument()
      })
    })
  })

  describe('Timestamp Formatting', () => {
    test('should format timestamps in Turkish locale', async () => {
      const logs: LearningLogEntry[] = [
        {
          timestamp: '2025-11-02T14:30:00Z',
          category: 'antiques',
          samples: 50,
          accuracy_before: 70,
          accuracy_after: 75,
        },
      ]

      ;(api.fetchLearningHistory as jest.Mock).mockResolvedValue({
        logs,
        total: 1,
      })

      render(<LearningLogs />)

      await waitFor(() => {
        // Should show formatted date (exact format depends on locale)
        const cells = screen.getAllByRole('cell')
        expect(cells[0]).toHaveTextContent(/\d{2}/)
      })
    })
  })

  describe('Hover Effects', () => {
    test('should have hover transition on table rows', async () => {
      ;(api.fetchLearningHistory as jest.Mock).mockResolvedValue({
        logs: mockLogs.slice(0, 1),
        total: 1,
      })

      const { container } = render(<LearningLogs />)

      await waitFor(() => {
        const row = container.querySelector('tbody tr')
        expect(row).toHaveClass('hover:bg-gray-50')
      })
    })
  })

  describe('Accessibility', () => {
    test('should have proper heading structure', async () => {
      ;(api.fetchLearningHistory as jest.Mock).mockResolvedValue({
        logs: mockLogs,
        total: mockLogs.length,
      })

      render(<LearningLogs />)

      await waitFor(() => {
        const heading = screen.getByText(/Learning History/)
        expect(heading.tagName).toBe('H2')
      })
    })

    test('should have accessible table structure', async () => {
      ;(api.fetchLearningHistory as jest.Mock).mockResolvedValue({
        logs: mockLogs.slice(0, 1),
        total: 1,
      })

      render(<LearningLogs />)

      await waitFor(() => {
        const table = screen.getByRole('table')
        expect(table).toBeInTheDocument()
      })
    })
  })
})
