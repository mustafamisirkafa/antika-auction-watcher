/**
 * Tests for AdvisorPanel component
 */

import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import AdvisorPanel from '@/components/AdvisorPanel'
import * as api from '@/lib/api'

jest.mock('@/lib/api')

describe('AdvisorPanel Component', () => {
  const mockRecommendation = {
    item_id: 'item123',
    recommendation: 'buy',
    confidence: 0.85,
    suggested_max_bid: 550,
    reasoning: [
      '? Buy: Good opportunity, recommended to bid',
      '?? Pattern: Analyzed 4 similar ceramics items.',
      '?? Market: Competition level: 2 bidders.'
    ],
    risk_level: 'low',
    pattern_sense: { score: 0.8, confidence: 0.75, reasoning: 'Good pattern', factors: {} },
    market_sense: { score: 0.85, confidence: 0.8, reasoning: 'Good market', factors: {} },
    behavior_sense: { score: 0.75, confidence: 0.7, reasoning: 'Familiar category', factors: {} },
    risk_sense: { score: 0.9, confidence: 0.85, reasoning: 'Low risk', factors: {} },
    timestamp: '2025-11-02T10:00:00Z',
    expires_at: '2025-11-02T10:30:00Z'
  }

  beforeEach(() => {
    jest.clearAllMocks()
    ;(api.fetchJson as jest.Mock).mockResolvedValue(mockRecommendation)
  })

  test('should display loading state initially', () => {
    ;(api.fetchJson as jest.Mock).mockImplementation(() => new Promise(() => {}))
    render(<AdvisorPanel itemId="item123" />)
    expect(screen.getByText('Analyzing...')).toBeInTheDocument()
  })

  test('should display recommendation after loading', async () => {
    render(<AdvisorPanel itemId="item123" />)
    await waitFor(() => {
      expect(screen.getByText(/Buy/)).toBeInTheDocument()
    })
  })

  test('should display confidence percentage', async () => {
    render(<AdvisorPanel itemId="item123" />)
    await waitFor(() => {
      expect(screen.getByText(/85% confident/i)).toBeInTheDocument()
    })
  })

  test('should display suggested max bid', async () => {
    render(<AdvisorPanel itemId="item123" />)
    await waitFor(() => {
      expect(screen.getByText(/\$550\.00/)).toBeInTheDocument()
    })
  })

  test('should display reasoning points', async () => {
    render(<AdvisorPanel itemId="item123" />)
    await waitFor(() => {
      expect(screen.getByText(/Good opportunity/)).toBeInTheDocument()
    })
  })

  test('should show compact version when compact prop is true', async () => {
    render(<AdvisorPanel itemId="item123" compact={true} />)
    await waitFor(() => {
      expect(screen.getByText('Show full analysis')).toBeInTheDocument()
    })
  })

  test('should toggle details in compact mode', async () => {
    render(<AdvisorPanel itemId="item123" compact={true} />)
    
    await waitFor(() => {
      expect(screen.getByText('Show full analysis')).toBeInTheDocument()
    })
    
    const toggleButton = screen.getByText('Show full analysis')
    fireEvent.click(toggleButton)
    
    await waitFor(() => {
      expect(screen.getByText('Hide details')).toBeInTheDocument()
    })
  })

  test('should display error message on API failure', async () => {
    ;(api.fetchJson as jest.Mock).mockRejectedValue(new Error('Network error'))
    
    render(<AdvisorPanel itemId="item123" />)
    
    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument()
    })
  })

  test('should call onFeedback when helpful button clicked', async () => {
    const onFeedback = jest.fn()
    render(<AdvisorPanel itemId="item123" compact={true} onFeedback={onFeedback} />)
    
    await waitFor(() => {
      const toggleButton = screen.getByText('Show full analysis')
      fireEvent.click(toggleButton)
    })
    
    await waitFor(() => {
      const helpfulButton = screen.getByText(/Helpful/)
      fireEvent.click(helpfulButton)
      expect(onFeedback).toHaveBeenCalledWith('helpful')
    })
  })

  test('should display strong buy with correct styling', async () => {
    const strongBuyRec = { ...mockRecommendation, recommendation: 'strong_buy' }
    ;(api.fetchJson as jest.Mock).mockResolvedValue(strongBuyRec)
    
    render(<AdvisorPanel itemId="item123" compact={true} />)
    
    await waitFor(() => {
      expect(screen.getByText('Strong Buy')).toBeInTheDocument()
    })
  })

  test('should display avoid recommendation with warning', async () => {
    const avoidRec = { ...mockRecommendation, recommendation: 'avoid', risk_level: 'very_high' }
    ;(api.fetchJson as jest.Mock).mockResolvedValue(avoidRec)
    
    render(<AdvisorPanel itemId="item123" compact={true} />)
    
    await waitFor(() => {
      expect(screen.getByText('Avoid')).toBeInTheDocument()
    })
  })

  test('should display all sense scores in full mode', async () => {
    render(<AdvisorPanel itemId="item123" />)
    
    await waitFor(() => {
      expect(screen.getByText(/Pattern Sense/)).toBeInTheDocument()
      expect(screen.getByText(/Market Sense/)).toBeInTheDocument()
      expect(screen.getByText(/Behavior Sense/)).toBeInTheDocument()
      expect(screen.getByText(/Risk Sense/)).toBeInTheDocument()
    })
  })

  test('should display risk level badge', async () => {
    render(<AdvisorPanel itemId="item123" />)
    
    await waitFor(() => {
      expect(screen.getByText('Low Risk')).toBeInTheDocument()
    })
  })

  test('should allow refreshing recommendation', async () => {
    render(<AdvisorPanel itemId="item123" />)
    
    await waitFor(() => {
      const refreshButton = screen.getByText(/Refresh/)
      fireEvent.click(refreshButton)
    })
    
    expect(api.fetchJson).toHaveBeenCalledTimes(2)
  })
})
