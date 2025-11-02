/**
 * Tests for ProfitCard Component (Phase 9)
 */
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import ProfitCard from '@/components/ProfitCard';

const mockEstimate = {
  id: 1,
  estimated_value: 1160.0,
  recommended_max_bid: 950.0,
  profit_margin: 0.22,
  profit_amount: 210.0,
  confidence: 0.82,
  risk_level: 'low' as const,
  market_volatility: 0.25,
  liquidity_avg: 0.87,
};

const mockAuctionItem = {
  id: 1,
  lot_id: 'LOT-001',
  title: 'Silver Candleholder',
  category: 'silver',
  image_url: 'https://example.com/image.jpg',
  starting_price: 800.0,
  auction_date: '2025-11-10T14:00:00Z',
  source: "Christie's",
};

describe('ProfitCard', () => {
  test('renders item details correctly', () => {
    render(<ProfitCard estimate={mockEstimate} auctionItem={mockAuctionItem} />);
    
    expect(screen.getByText('Silver Candleholder')).toBeInTheDocument();
    expect(screen.getByText('LOT-001')).toBeInTheDocument();
    expect(screen.getByText('silver')).toBeInTheDocument();
  });

  test('displays price information', () => {
    render(<ProfitCard estimate={mockEstimate} auctionItem={mockAuctionItem} />);
    
    expect(screen.getByText('Starting Price')).toBeInTheDocument();
    expect(screen.getByText('AI Max Bid')).toBeInTheDocument();
    expect(screen.getByText('Market Avg')).toBeInTheDocument();
  });

  test('shows high confidence with green color', () => {
    const highConfEstimate = { ...mockEstimate, confidence: 0.85 };
    
    const { container } = render(
      <ProfitCard estimate={highConfEstimate} auctionItem={mockAuctionItem} />
    );
    
    const confidenceBadge = screen.getByText('85.0%');
    expect(confidenceBadge).toHaveClass('text-green-600');
  });

  test('shows medium confidence with yellow color', () => {
    const mediumConfEstimate = { ...mockEstimate, confidence: 0.65 };
    
    const { container } = render(
      <ProfitCard estimate={mediumConfEstimate} auctionItem={mockAuctionItem} />
    );
    
    const confidenceBadge = screen.getByText('65.0%');
    expect(confidenceBadge).toHaveClass('text-yellow-600');
  });

  test('shows low confidence with red color', () => {
    const lowConfEstimate = { ...mockEstimate, confidence: 0.45 };
    
    const { container } = render(
      <ProfitCard estimate={lowConfEstimate} auctionItem={mockAuctionItem} />
    );
    
    const confidenceBadge = screen.getByText('45.0%');
    expect(confidenceBadge).toHaveClass('text-red-600');
  });

  test('displays risk level correctly', () => {
    render(<ProfitCard estimate={mockEstimate} auctionItem={mockAuctionItem} />);
    
    expect(screen.getByText('LOW')).toBeInTheDocument();
  });

  test('shows profit margin as percentage', () => {
    render(<ProfitCard estimate={mockEstimate} auctionItem={mockAuctionItem} />);
    
    expect(screen.getByText('+22.0%')).toBeInTheDocument();
  });

  test('renders profit margin progress bar', () => {
    const { container } = render(
      <ProfitCard estimate={mockEstimate} auctionItem={mockAuctionItem} />
    );
    
    const progressBar = container.querySelector('.bg-green-500');
    expect(progressBar).toBeInTheDocument();
  });

  test('shows auto-bid button when enabled', () => {
    const onAutoBid = jest.fn();
    
    render(
      <ProfitCard
        estimate={mockEstimate}
        auctionItem={mockAuctionItem}
        onAutoBid={onAutoBid}
        canAutoBid={true}
      />
    );
    
    const autoBidButton = screen.getByRole('button', { name: /Auto-Bid until/i });
    expect(autoBidButton).toBeEnabled();
    
    fireEvent.click(autoBidButton);
    expect(onAutoBid).toHaveBeenCalledWith(950.0);
  });

  test('disables auto-bid button for non-PRO users', () => {
    render(
      <ProfitCard
        estimate={mockEstimate}
        auctionItem={mockAuctionItem}
        onAutoBid={() => {}}
        canAutoBid={false}
      />
    );
    
    const autoBidButton = screen.getByRole('button', { name: /Upgrade to PRO/i });
    expect(autoBidButton).toBeDisabled();
  });

  test('displays market metrics', () => {
    render(<ProfitCard estimate={mockEstimate} auctionItem={mockAuctionItem} />);
    
    expect(screen.getByText('Liquidity')).toBeInTheDocument();
    expect(screen.getByText('Volatility')).toBeInTheDocument();
    expect(screen.getByText('87.0%')).toBeInTheDocument(); // Liquidity value
  });

  test('renders placeholder when no image', () => {
    const noImageItem = { ...mockAuctionItem, image_url: undefined };
    
    const { container } = render(
      <ProfitCard estimate={mockEstimate} auctionItem={noImageItem} />
    );
    
    // Should render SVG placeholder
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  test('displays auction date formatted', () => {
    render(<ProfitCard estimate={mockEstimate} auctionItem={mockAuctionItem} />);
    
    expect(screen.getByText(/10.*Kas/i)).toBeInTheDocument(); // Turkish date format
  });

  test('shows negative profit margin correctly', () => {
    const negativeEstimate = {
      ...mockEstimate,
      profit_margin: -0.10,
      profit_amount: -100.0,
    };
    
    render(<ProfitCard estimate={negativeEstimate} auctionItem={mockAuctionItem} />);
    
    expect(screen.getByText('-10.0%')).toBeInTheDocument();
  });

  test('applies correct color for different profit margins', () => {
    // High profit (>20%) = green
    const highProfit = { ...mockEstimate, profit_margin: 0.25 };
    const { container: greenContainer } = render(
      <ProfitCard estimate={highProfit} auctionItem={mockAuctionItem} />
    );
    expect(greenContainer.querySelector('.bg-green-500')).toBeInTheDocument();

    // Medium profit (10-20%) = yellow
    const mediumProfit = { ...mockEstimate, profit_margin: 0.15 };
    const { container: yellowContainer } = render(
      <ProfitCard estimate={mediumProfit} auctionItem={mockAuctionItem} />
    );
    expect(yellowContainer.querySelector('.bg-yellow-500')).toBeInTheDocument();

    // Low profit (<10%) = orange
    const lowProfit = { ...mockEstimate, profit_margin: 0.05 };
    const { container: orangeContainer } = render(
      <ProfitCard estimate={lowProfit} auctionItem={mockAuctionItem} />
    );
    expect(orangeContainer.querySelector('.bg-orange-500')).toBeInTheDocument();
  });
});
