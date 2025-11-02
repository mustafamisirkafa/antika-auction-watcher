/**
 * Tests for Exports component - CSV download with date pickers
 */

import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import Exports from '@/components/Exports'
import * as api from '@/lib/api'

// Mock API
jest.mock('@/lib/api')

// Mock window.location.href
delete (window as any).location
window.location = { href: '' } as any

describe('Exports Component', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    window.location.href = ''
  })

  describe('Initial Render', () => {
    test('should render component title', () => {
      render(<Exports />)
      expect(screen.getByText('?? Data Exports')).toBeInTheDocument()
    })

    test('should render valuations export section', () => {
      render(<Exports />)
      expect(screen.getByText('Valuations Export')).toBeInTheDocument()
    })

    test('should render outcomes export section', () => {
      render(<Exports />)
      expect(screen.getByText('Bid Outcomes Export')).toBeInTheDocument()
    })

    test('should render export information panel', () => {
      render(<Exports />)
      expect(screen.getByText('Export Information')).toBeInTheDocument()
    })
  })

  describe('Date Inputs', () => {
    test('should have from and to date inputs for valuations', () => {
      render(<Exports />)
      
      const dateInputs = screen.getAllByLabelText(/From Date|To Date/)
      expect(dateInputs.length).toBeGreaterThanOrEqual(2)
    })

    test('should accept date input for valuations from date', () => {
      render(<Exports />)
      
      const fromInputs = screen.getAllByLabelText('From Date')
      fireEvent.change(fromInputs[0], { target: { value: '2025-10-01' } })
      
      expect((fromInputs[0] as HTMLInputElement).value).toBe('2025-10-01')
    })

    test('should accept date input for valuations to date', () => {
      render(<Exports />)
      
      const toInputs = screen.getAllByLabelText('To Date')
      fireEvent.change(toInputs[0], { target: { value: '2025-10-31' } })
      
      expect((toInputs[0] as HTMLInputElement).value).toBe('2025-10-31')
    })

    test('should have from and to date inputs for outcomes', () => {
      render(<Exports />)
      
      const fromInputs = screen.getAllByLabelText('From Date')
      const toInputs = screen.getAllByLabelText('To Date')
      
      expect(fromInputs.length).toBe(2)
      expect(toInputs.length).toBe(2)
    })

    test('should have category selector for outcomes', () => {
      render(<Exports />)
      
      expect(screen.getByLabelText('Category (Optional)')).toBeInTheDocument()
    })
  })

  describe('Last Month Quick Select', () => {
    test('should have Last Month button for valuations', () => {
      render(<Exports />)
      
      const lastMonthButtons = screen.getAllByText('Last Month')
      expect(lastMonthButtons.length).toBeGreaterThanOrEqual(1)
    })

    test('should populate dates when Last Month clicked for valuations', () => {
      render(<Exports />)
      
      const fromInputs = screen.getAllByLabelText('From Date')
      const toInputs = screen.getAllByLabelText('To Date')
      const lastMonthButtons = screen.getAllByText('Last Month')
      
      fireEvent.click(lastMonthButtons[0])
      
      expect((fromInputs[0] as HTMLInputElement).value).not.toBe('')
      expect((toInputs[0] as HTMLInputElement).value).not.toBe('')
    })

    test('should populate dates when Last Month clicked for outcomes', () => {
      render(<Exports />)
      
      const fromInputs = screen.getAllByLabelText('From Date')
      const toInputs = screen.getAllByLabelText('To Date')
      const lastMonthButtons = screen.getAllByText('Last Month')
      
      fireEvent.click(lastMonthButtons[1])
      
      expect((fromInputs[1] as HTMLInputElement).value).not.toBe('')
      expect((toInputs[1] as HTMLInputElement).value).not.toBe('')
    })
  })

  describe('Category Selector', () => {
    test('should have "All Categories" as default option', () => {
      render(<Exports />)
      
      const categorySelect = screen.getByLabelText('Category (Optional)') as HTMLSelectElement
      expect(categorySelect.value).toBe('')
      expect(screen.getByText('All Categories')).toBeInTheDocument()
    })

    test('should list predefined categories', () => {
      render(<Exports />)
      
      const categorySelect = screen.getByLabelText('Category (Optional)')
      
      expect(categorySelect).toContainHTML('antiques')
      expect(categorySelect).toContainHTML('ceramics')
      expect(categorySelect).toContainHTML('coins')
      expect(categorySelect).toContainHTML('paintings')
    })

    test('should allow category selection', () => {
      render(<Exports />)
      
      const categorySelect = screen.getByLabelText('Category (Optional)') as HTMLSelectElement
      fireEvent.change(categorySelect, { target: { value: 'antiques' } })
      
      expect(categorySelect.value).toBe('antiques')
    })
  })

  describe('Valuations Export', () => {
    test('should call API with correct parameters when exporting', () => {
      const mockUrl = 'http://api.com/export?from=2025-10-01&to=2025-10-31'
      ;(api.getValuationsExportUrl as jest.Mock).mockReturnValue(mockUrl)
      
      render(<Exports />)
      
      const fromInputs = screen.getAllByLabelText('From Date')
      const toInputs = screen.getAllByLabelText('To Date')
      
      fireEvent.change(fromInputs[0], { target: { value: '2025-10-01' } })
      fireEvent.change(toInputs[0], { target: { value: '2025-10-31' } })
      
      const downloadButtons = screen.getAllByText('Download CSV')
      fireEvent.click(downloadButtons[0])
      
      expect(api.getValuationsExportUrl).toHaveBeenCalledWith({
        from: '2025-10-01',
        to: '2025-10-31',
      })
    })

    test('should trigger download by setting window.location.href', () => {
      const mockUrl = 'http://api.com/export'
      ;(api.getValuationsExportUrl as jest.Mock).mockReturnValue(mockUrl)
      
      render(<Exports />)
      
      const downloadButtons = screen.getAllByText('Download CSV')
      fireEvent.click(downloadButtons[0])
      
      expect(window.location.href).toBe(mockUrl)
    })

    test('should show success toast on export', async () => {
      ;(api.getValuationsExportUrl as jest.Mock).mockReturnValue('http://api.com/export')
      
      render(<Exports />)
      
      const downloadButtons = screen.getAllByText('Download CSV')
      fireEvent.click(downloadButtons[0])
      
      await waitFor(() => {
        expect(screen.getByText('Valuations export started')).toBeInTheDocument()
      })
    })

    test('should validate that from date is before to date', async () => {
      ;(api.getValuationsExportUrl as jest.Mock).mockReturnValue('http://api.com/export')
      
      render(<Exports />)
      
      const fromInputs = screen.getAllByLabelText('From Date')
      const toInputs = screen.getAllByLabelText('To Date')
      
      fireEvent.change(fromInputs[0], { target: { value: '2025-10-31' } })
      fireEvent.change(toInputs[0], { target: { value: '2025-10-01' } })
      
      const downloadButtons = screen.getAllByText('Download CSV')
      fireEvent.click(downloadButtons[0])
      
      await waitFor(() => {
        expect(screen.getByText('Start date must be before end date')).toBeInTheDocument()
      })
      
      expect(window.location.href).toBe('')
    })

    test('should export all data when no dates specified', () => {
      ;(api.getValuationsExportUrl as jest.Mock).mockReturnValue('http://api.com/export')
      
      render(<Exports />)
      
      const downloadButtons = screen.getAllByText('Download CSV')
      fireEvent.click(downloadButtons[0])
      
      expect(api.getValuationsExportUrl).toHaveBeenCalledWith({
        from: undefined,
        to: undefined,
      })
    })
  })

  describe('Outcomes Export', () => {
    test('should call API with correct parameters when exporting', () => {
      const mockUrl = 'http://api.com/export?from=2025-10-01&to=2025-10-31&category=antiques'
      ;(api.getOutcomesExportUrl as jest.Mock).mockReturnValue(mockUrl)
      
      render(<Exports />)
      
      const fromInputs = screen.getAllByLabelText('From Date')
      const toInputs = screen.getAllByLabelText('To Date')
      const categorySelect = screen.getByLabelText('Category (Optional)')
      
      fireEvent.change(fromInputs[1], { target: { value: '2025-10-01' } })
      fireEvent.change(toInputs[1], { target: { value: '2025-10-31' } })
      fireEvent.change(categorySelect, { target: { value: 'antiques' } })
      
      const downloadButtons = screen.getAllByText('Download CSV')
      fireEvent.click(downloadButtons[1])
      
      expect(api.getOutcomesExportUrl).toHaveBeenCalledWith({
        from: '2025-10-01',
        to: '2025-10-31',
        category: 'antiques',
      })
    })

    test('should trigger download by setting window.location.href', () => {
      const mockUrl = 'http://api.com/export-outcomes'
      ;(api.getOutcomesExportUrl as jest.Mock).mockReturnValue(mockUrl)
      
      render(<Exports />)
      
      const downloadButtons = screen.getAllByText('Download CSV')
      fireEvent.click(downloadButtons[1])
      
      expect(window.location.href).toBe(mockUrl)
    })

    test('should show success toast on export', async () => {
      ;(api.getOutcomesExportUrl as jest.Mock).mockReturnValue('http://api.com/export')
      
      render(<Exports />)
      
      const downloadButtons = screen.getAllByText('Download CSV')
      fireEvent.click(downloadButtons[1])
      
      await waitFor(() => {
        expect(screen.getByText('Outcomes export started')).toBeInTheDocument()
      })
    })

    test('should validate that from date is before to date', async () => {
      ;(api.getOutcomesExportUrl as jest.Mock).mockReturnValue('http://api.com/export')
      
      render(<Exports />)
      
      const fromInputs = screen.getAllByLabelText('From Date')
      const toInputs = screen.getAllByLabelText('To Date')
      
      fireEvent.change(fromInputs[1], { target: { value: '2025-10-31' } })
      fireEvent.change(toInputs[1], { target: { value: '2025-10-01' } })
      
      const downloadButtons = screen.getAllByText('Download CSV')
      fireEvent.click(downloadButtons[1])
      
      await waitFor(() => {
        expect(screen.getByText('Start date must be before end date')).toBeInTheDocument()
      })
      
      expect(window.location.href).toBe('')
    })

    test('should export all outcomes when no filters specified', () => {
      ;(api.getOutcomesExportUrl as jest.Mock).mockReturnValue('http://api.com/export')
      
      render(<Exports />)
      
      const downloadButtons = screen.getAllByText('Download CSV')
      fireEvent.click(downloadButtons[1])
      
      expect(api.getOutcomesExportUrl).toHaveBeenCalledWith({
        from: undefined,
        to: undefined,
        category: undefined,
      })
    })

    test('should include category in export when selected', () => {
      ;(api.getOutcomesExportUrl as jest.Mock).mockReturnValue('http://api.com/export')
      
      render(<Exports />)
      
      const categorySelect = screen.getByLabelText('Category (Optional)')
      fireEvent.change(categorySelect, { target: { value: 'coins' } })
      
      const downloadButtons = screen.getAllByText('Download CSV')
      fireEvent.click(downloadButtons[1])
      
      expect(api.getOutcomesExportUrl).toHaveBeenCalledWith({
        from: undefined,
        to: undefined,
        category: 'coins',
      })
    })
  })

  describe('Toast Notifications', () => {
    test('should show success toast with green styling', async () => {
      ;(api.getValuationsExportUrl as jest.Mock).mockReturnValue('http://api.com/export')
      
      const { container } = render(<Exports />)
      
      const downloadButtons = screen.getAllByText('Download CSV')
      fireEvent.click(downloadButtons[0])
      
      await waitFor(() => {
        const toast = container.querySelector('.bg-green-50.border-green-300')
        expect(toast).toBeInTheDocument()
      })
    })

    test('should show error toast with red styling', async () => {
      ;(api.getValuationsExportUrl as jest.Mock).mockReturnValue('http://api.com/export')
      
      const { container } = render(<Exports />)
      
      const fromInputs = screen.getAllByLabelText('From Date')
      const toInputs = screen.getAllByLabelText('To Date')
      
      // Invalid date range
      fireEvent.change(fromInputs[0], { target: { value: '2025-10-31' } })
      fireEvent.change(toInputs[0], { target: { value: '2025-10-01' } })
      
      const downloadButtons = screen.getAllByText('Download CSV')
      fireEvent.click(downloadButtons[0])
      
      await waitFor(() => {
        const toast = container.querySelector('.bg-red-50.border-red-300')
        expect(toast).toBeInTheDocument()
      })
    })

    test('should auto-dismiss toast after 5 seconds', async () => {
      jest.useFakeTimers()
      ;(api.getValuationsExportUrl as jest.Mock).mockReturnValue('http://api.com/export')
      
      render(<Exports />)
      
      const downloadButtons = screen.getAllByText('Download CSV')
      fireEvent.click(downloadButtons[0])
      
      await waitFor(() => {
        expect(screen.getByText('Valuations export started')).toBeInTheDocument()
      })
      
      // Fast-forward 5 seconds
      jest.advanceTimersByTime(5000)
      
      await waitFor(() => {
        expect(screen.queryByText('Valuations export started')).not.toBeInTheDocument()
      })
      
      jest.useRealTimers()
    })
  })

  describe('Export Status Messages', () => {
    test('should show "all valuations will be exported" when no dates', () => {
      render(<Exports />)
      expect(screen.getByText('All valuations will be exported')).toBeInTheDocument()
    })

    test('should show date range when dates selected for valuations', () => {
      render(<Exports />)
      
      const fromInputs = screen.getAllByLabelText('From Date')
      const toInputs = screen.getAllByLabelText('To Date')
      
      fireEvent.change(fromInputs[0], { target: { value: '2025-10-01' } })
      fireEvent.change(toInputs[0], { target: { value: '2025-10-31' } })
      
      expect(screen.getByText('Exporting from 2025-10-01 to 2025-10-31')).toBeInTheDocument()
    })

    test('should show "all outcomes will be exported" when no filters', () => {
      render(<Exports />)
      expect(screen.getByText('All outcomes will be exported')).toBeInTheDocument()
    })

    test('should show category in status when selected', () => {
      render(<Exports />)
      
      const categorySelect = screen.getByLabelText('Category (Optional)')
      fireEvent.change(categorySelect, { target: { value: 'antiques' } })
      
      expect(screen.getByText(/for category: antiques/)).toBeInTheDocument()
    })
  })

  describe('Export Information Panel', () => {
    test('should display helpful information', () => {
      render(<Exports />)
      
      expect(screen.getByText(/CSV files will download automatically/)).toBeInTheDocument()
      expect(screen.getByText(/Date filters are optional/)).toBeInTheDocument()
      expect(screen.getByText(/Large exports may take a few seconds/)).toBeInTheDocument()
      expect(screen.getByText(/Files include headers/)).toBeInTheDocument()
      expect(screen.getByText(/Timestamps are in UTC format/)).toBeInTheDocument()
    })
  })

  describe('Error Handling', () => {
    test('should show error toast when export URL generation fails', async () => {
      ;(api.getValuationsExportUrl as jest.Mock).mockImplementation(() => {
        throw new Error('Invalid parameters')
      })
      
      render(<Exports />)
      
      const downloadButtons = screen.getAllByText('Download CSV')
      fireEvent.click(downloadButtons[0])
      
      await waitFor(() => {
        expect(screen.getByText('Invalid parameters')).toBeInTheDocument()
      })
    })

    test('should not trigger download on error', async () => {
      ;(api.getValuationsExportUrl as jest.Mock).mockImplementation(() => {
        throw new Error('Error')
      })
      
      render(<Exports />)
      
      const downloadButtons = screen.getAllByText('Download CSV')
      fireEvent.click(downloadButtons[0])
      
      await waitFor(() => {
        expect(screen.getByText(/Error/)).toBeInTheDocument()
      })
      
      expect(window.location.href).toBe('')
    })
  })

  describe('Icons and Visual Elements', () => {
    test('should have download icons on buttons', () => {
      const { container } = render(<Exports />)
      
      const downloadButtons = screen.getAllByText('Download CSV')
      downloadButtons.forEach((button) => {
        const svg = button.querySelector('svg')
        expect(svg).toBeInTheDocument()
      })
    })

    test('should have section icons', () => {
      const { container } = render(<Exports />)
      
      // Check for SVG icons in section headers
      const svgs = container.querySelectorAll('svg')
      expect(svgs.length).toBeGreaterThan(0)
    })
  })

  describe('Accessibility', () => {
    test('should have proper label associations', () => {
      render(<Exports />)
      
      const fromDate = screen.getAllByLabelText('From Date')[0]
      const toDate = screen.getAllByLabelText('To Date')[0]
      const category = screen.getByLabelText('Category (Optional)')
      
      expect(fromDate).toBeInTheDocument()
      expect(toDate).toBeInTheDocument()
      expect(category).toBeInTheDocument()
    })

    test('should have proper heading structure', () => {
      render(<Exports />)
      
      const heading = screen.getByText('?? Data Exports')
      expect(heading.tagName).toBe('H2')
    })

    test('should have descriptive button text', () => {
      render(<Exports />)
      
      const downloadButtons = screen.getAllByText('Download CSV')
      expect(downloadButtons).toHaveLength(2)
    })
  })

  describe('Responsive Design', () => {
    test('should have grid layout for date inputs', () => {
      const { container } = render(<Exports />)
      
      const grids = container.querySelectorAll('.grid')
      expect(grids.length).toBeGreaterThan(0)
    })
  })
})
