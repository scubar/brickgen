import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Header from '../components/Header';

describe('Header Component', () => {
  const renderHeader = () => {
    return render(
      <BrowserRouter>
        <Header />
      </BrowserRouter>
    );
  };

  it('renders the BrickGen title', () => {
    renderHeader();
    expect(screen.getByText('BrickGen')).toBeInTheDocument();
  });

  it('renders navigation links', () => {
    renderHeader();
    expect(screen.getByText('Projects')).toBeInTheDocument();
    expect(screen.getByText('Settings')).toBeInTheDocument();
    expect(screen.getByText('Attributions')).toBeInTheDocument();
  });

  it('has correct link hrefs', () => {
    renderHeader();
    const projectsLink = screen.getByText('Projects').closest('a');
    const settingsLink = screen.getByText('Settings').closest('a');
    const attributionsLink = screen.getByText('Attributions').closest('a');
    
    expect(projectsLink).toHaveAttribute('href', '/projects');
    expect(settingsLink).toHaveAttribute('href', '/settings');
    expect(attributionsLink).toHaveAttribute('href', '/attributions');
  });

  it('renders logo link to home', () => {
    renderHeader();
    const logoLink = screen.getByText('BrickGen').closest('a');
    expect(logoLink).toHaveAttribute('href', '/');
  });
});
