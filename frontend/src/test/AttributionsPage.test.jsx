import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import AttributionsPage from '../pages/AttributionsPage';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('AttributionsPage', () => {
  const renderPage = () => {
    return render(
      <BrowserRouter>
        <AttributionsPage />
      </BrowserRouter>
    );
  };

  beforeEach(() => {
    mockNavigate.mockClear();
  });

  it('renders the page title', () => {
    renderPage();
    expect(screen.getByText('Attributions')).toBeInTheDocument();
  });

  it('renders back button', () => {
    renderPage();
    const backButton = screen.getByText('← Back');
    expect(backButton).toBeInTheDocument();
  });

  it('navigates back when back button is clicked', () => {
    renderPage();
    const backButton = screen.getByText('← Back');
    fireEvent.click(backButton);
    expect(mockNavigate).toHaveBeenCalledWith(-1);
  });

  it('renders all attribution items', () => {
    renderPage();
    expect(screen.getByText('LDraw')).toBeInTheDocument();
    expect(screen.getByText('LDView')).toBeInTheDocument();
    expect(screen.getByText('Rebrickable API')).toBeInTheDocument();
    expect(screen.getByText('FastAPI')).toBeInTheDocument();
    expect(screen.getByText('React')).toBeInTheDocument();
    expect(screen.getByText('Vite')).toBeInTheDocument();
    expect(screen.getByText('TailwindCSS')).toBeInTheDocument();
  });

  it('renders descriptions for attribution items', () => {
    renderPage();
    expect(screen.getByText('LEGO part library and format')).toBeInTheDocument();
    expect(screen.getByText(/LDraw viewer and STL export/)).toBeInTheDocument();
    expect(screen.getByText('LEGO set and parts data')).toBeInTheDocument();
  });

  it('renders links with correct hrefs', () => {
    renderPage();
    const ldrawLink = screen.getByText('LDraw').closest('a');
    expect(ldrawLink).toHaveAttribute('href', 'https://www.ldraw.org/');
    expect(ldrawLink).toHaveAttribute('target', '_blank');
    expect(ldrawLink).toHaveAttribute('rel', 'noopener noreferrer');
    
    const rebrickableLink = screen.getByText('Rebrickable API').closest('a');
    expect(rebrickableLink).toHaveAttribute('href', 'https://rebrickable.com/api/');
  });

  it('renders explanation text', () => {
    renderPage();
    expect(screen.getByText(/This product uses the following third-party software/)).toBeInTheDocument();
    expect(screen.getByText(/see ATTRIBUTIONS.md in the repository/)).toBeInTheDocument();
  });

  it('renders correct number of attribution items', () => {
    renderPage();
    // There are 7 items in the list
    const listItems = screen.getAllByRole('listitem');
    expect(listItems.length).toBe(7);
  });
});
