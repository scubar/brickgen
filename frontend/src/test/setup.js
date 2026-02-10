import '@testing-library/jest-dom';

// Mock window.matchMedia which is not available in jsdom
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => {},
  }),
});

// Mock fetch if needed
global.fetch = global.fetch || (() => Promise.resolve({
  json: () => Promise.resolve({}),
}));
