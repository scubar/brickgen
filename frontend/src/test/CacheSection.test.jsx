import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import CacheSection from '../components/CacheSection';

describe('CacheSection Component', () => {
  const defaultProps = {
    id: 'test-cache',
    title: 'Test Cache',
    description: 'This is a test cache description',
  };

  it('renders title and description', () => {
    render(<CacheSection {...defaultProps} />);
    expect(screen.getByText('Test Cache')).toBeInTheDocument();
    expect(screen.getByText('This is a test cache description')).toBeInTheDocument();
  });

  it('renders manage cache button', () => {
    render(<CacheSection {...defaultProps} />);
    const button = screen.getByText('Manage cache');
    expect(button).toBeInTheDocument();
  });

  it('opens modal when manage cache button is clicked', () => {
    render(
      <CacheSection {...defaultProps}>
        <div>Modal Content</div>
      </CacheSection>
    );
    
    const button = screen.getByText('Manage cache');
    fireEvent.click(button);
    
    // Modal should now be visible with the title again (in modal header)
    const modalTitles = screen.getAllByText('Test Cache');
    expect(modalTitles.length).toBeGreaterThan(1); // One in card, one in modal
    
    // Check for modal content
    expect(screen.getByText('Modal Content')).toBeInTheDocument();
  });

  it('closes modal when close button is clicked', () => {
    render(
      <CacheSection {...defaultProps}>
        <div>Modal Content</div>
      </CacheSection>
    );
    
    // Open modal
    const openButton = screen.getByText('Manage cache');
    fireEvent.click(openButton);
    
    // Close modal
    const closeButton = screen.getByLabelText('Close');
    fireEvent.click(closeButton);
    
    // Modal content should not be visible
    expect(screen.queryByText('Modal Content')).not.toBeInTheDocument();
  });

  it('closes modal when clicking backdrop', () => {
    render(
      <CacheSection {...defaultProps}>
        <div>Modal Content</div>
      </CacheSection>
    );
    
    // Open modal
    const openButton = screen.getByText('Manage cache');
    fireEvent.click(openButton);
    
    // Click backdrop (the fixed overlay)
    const backdrop = screen.getByText('Modal Content').closest('.fixed');
    fireEvent.click(backdrop);
    
    // Modal content should not be visible
    expect(screen.queryByText('Modal Content')).not.toBeInTheDocument();
  });

  it('renders thumbnail when provided', () => {
    const propsWithThumbnail = {
      ...defaultProps,
      thumbnailUrl: 'https://example.com/image.jpg',
      thumbnailAlt: 'Test thumbnail',
    };
    
    render(<CacheSection {...propsWithThumbnail} />);
    const img = screen.getByAltText('Test thumbnail');
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute('src', 'https://example.com/image.jpg');
  });

  it('does not render thumbnail when not provided', () => {
    render(<CacheSection {...defaultProps} />);
    const images = screen.queryAllByRole('img');
    expect(images.length).toBe(0);
  });

  it('prevents modal content clicks from closing modal', () => {
    render(
      <CacheSection {...defaultProps}>
        <button>Inner Button</button>
      </CacheSection>
    );
    
    // Open modal
    fireEvent.click(screen.getByText('Manage cache'));
    
    // Click inner content
    const innerButton = screen.getByText('Inner Button');
    fireEvent.click(innerButton);
    
    // Modal should still be open
    expect(screen.getByText('Inner Button')).toBeInTheDocument();
  });
});
