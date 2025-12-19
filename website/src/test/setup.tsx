import React from 'react';
import '@testing-library/jest-dom';
import { beforeAll, afterEach, afterAll, vi } from 'vitest';
import { server } from '../mocks/server';
import { fetch, Request, Response, Headers } from 'cross-fetch';

// Polyfill fetch for node environment
global.fetch = fetch as any;
global.Request = Request as any;
global.Response = Response as any;
global.Headers = Headers as any;

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// Mock Recharts
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: any) => <div className="recharts-responsive-container"> {children} </div>,
  BarChart: ({ children }: any) => <div className="bar-chart"> {children} </div>,
  Bar: () => <div className="bar" />,
  XAxis: () => <div className="x-axis" />,
  YAxis: () => <div className="y-axis" />,
  CartesianGrid: () => <div className="cartesian-grid" />,
  Tooltip: () => <div className="tooltip" />,
  Legend: () => <div className="legend" />,
  PieChart: ({ children }: any) => <div className="pie-chart"> {children} </div>,
  Pie: () => <div className="pie" />,
  Cell: () => <div className="cell" />,
  LineChart: ({ children }: any) => <div className="line-chart"> {children} </div>,
  Line: () => <div className="line" />,
  AreaChart: ({ children }: any) => <div className="area-chart"> {children} </div>,
  Area: () => <div className="area" />,
}));
