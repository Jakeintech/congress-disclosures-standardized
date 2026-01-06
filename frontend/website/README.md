# Congress Activity Website

Next.js website for browsing congressional financial disclosures, bills, and lobbying data.

## Quick Start

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Run tests
npm test

# Run tests in watch mode
npm run test:watch
```

## Architecture

- **Framework**: Next.js 16 with App Router
- **Deployment**: Vercel (recommended) or S3 static hosting
- **Styling**: Tailwind CSS with shadcn/ui components
- **API**: AWS API Gateway + Lambda
- **Testing**: Jest + React Testing Library

## Project Structure

```
website/
├── src/
│   ├── app/                   # Next.js App Router pages
│   │   ├── page.tsx           # Dashboard
│   │   ├── members/           # Members list
│   │   ├── politician/[id]/   # Member profile
│   │   ├── bills/             # Bills list and detail
│   │   ├── transactions/      # Transactions list
│   │   ├── lobbying/          # Lobbying pages
│   │   └── influence/         # Influence tracker
│   ├── components/            # React components
│   │   ├── ui/                # shadcn/ui components
│   │   ├── ErrorBoundary.tsx  # Error handling
│   │   └── nav/               # Navigation
│   └── lib/
│       ├── api.ts             # API client functions
│       └── utils.ts           # Utility functions
├── __tests__/                 # Test files
│   └── lib/
│       └── api.test.ts        # API integration tests
├── docs/
│   └── API_ENDPOINTS.md       # API documentation
├── public/                    # Static assets
├── next.config.ts             # Next.js configuration
├── vercel.json                # Vercel deployment config
└── package.json
```

## Development

### Running Locally

1. **Install dependencies**:
   ```bash
   npm install
   ```

2. **Set environment variables** (optional):
   ```bash
   # Create .env.local (optional, uses default API if not set)
   echo "NEXT_PUBLIC_API_BASE=https://yvpi88rhwl.execute-api.us-east-1.amazonaws.com" > .env.local
   ```

3. **Start dev server**:
   ```bash
   npm run dev
   ```

4. **Open browser**: http://localhost:3000

### Building for Production

```bash
npm run build
```

This creates an `out/` directory with static HTML files that can be deployed to any static host.

## Testing

### Unit Tests

```bash
# Run all tests
npm test

# Run specific test file
npm test -- __tests__/lib/api.test.ts

# Run with coverage
npm test -- --coverage

# Watch mode (re-run on file changes)
npm run test:watch
```

### Test Structure

- **API Tests** (`__tests__/lib/api.test.ts`): Integration tests for all API endpoints
- **Component Tests** (to be added): React component unit tests

### Writing Tests

Example API test:
```typescript
it('should fetch dashboard summary', async () => {
  const data = await fetchDashboardSummary();
  expect(data.totalMembers).toBeGreaterThan(0);
});
```

## Deployment

### Deploy to Vercel (Recommended)

1. **Connect to GitHub**:
   - Go to [vercel.com](https://vercel.com)
   - Click "New Project"
   - Import your GitHub repository
   - Select the `website/` directory as the root

2. **Configure**:
   - Framework: Next.js
   - Build Command: `npm run build`
   - Output Directory: `out`

3. **Environment Variables**:
   ```
   NEXT_PUBLIC_API_BASE=https://yvpi88rhwl.execute-api.us-east-1.amazonaws.com
   ```

4. **Deploy**:
   - Push to `main` branch → Auto-deploys to production
   - Push to other branches → Preview deployments

### Deploy to S3

1. **Update configuration**:
   - Uncomment `basePath: '/website'` in `next.config.ts`

2. **Build**:
   ```bash
   npm run build
   ```

3. **Upload to S3**:
   ```bash
   aws s3 sync out/ s3://your-bucket/website/ --delete
   ```

4. **Configure S3**:
   - Enable static website hosting
   - Set index document: `index.html`
   - Set error document: `404.html`
   - Configure CORS (see below)

### S3 CORS Configuration

```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "HEAD"],
    "AllowedOrigins": ["*"],
    "ExposeHeaders": []
  }
]
```

## Error Handling

All pages are wrapped in `<ErrorBoundary>` components that:
- Catch React errors and display user-friendly messages
- Provide retry functionality
- Show detailed errors in development mode
- Log errors for debugging

### ApiError Component

Used for displaying API errors:
```tsx
{error && <ApiError error={error} onRetry={() => refetch()} />}
```

## API Integration

API client is in `src/lib/api.ts`. All endpoints return data in this format:

```typescript
{
  success: boolean;
  data: T;
  error?: string;
}
```

### Key Functions

- `fetchDashboardSummary()` - Get dashboard stats
- `fetchMembers(params)` - List members with filters
- `fetchBills(params)` - List bills with filters
- `fetchTransactions(params)` - List trades
- `fetchTrendingStocks(limit)` - Get trending stocks
- `fetchTopTraders(limit)` - Get top traders

See `docs/API_ENDPOINTS.md` for complete API documentation.

## Component Library

Uses [shadcn/ui](https://ui.shadcn.com/) components built on Radix UI:

- `Button` - All button variants
- `Card` - Container component
- `Input` - Form inputs
- `Select` - Dropdowns
- `Table` - Data tables
- `Badge` - Status badges
- `Skeleton` - Loading states
- `Alert` - Notifications

### Adding New Components

```bash
npx shadcn@latest add [component-name]
```

## Styling

- **Tailwind CSS** for utility-first styling
- **CSS Variables** for theming (see `globals.css`)
- **Dark Mode** (not yet implemented)

### Common Patterns

```tsx
// Card with loading state
<Card>
  <CardHeader>
    <CardTitle>Title</CardTitle>
  </CardHeader>
  <CardContent>
    {loading ? <Skeleton className="h-4 w-full" /> : <div>{data}</div>}
  </CardContent>
</Card>

// Error boundary wrapper
export default function PageWithErrorBoundary() {
  return (
    <ErrorBoundary>
      <PageContent />
    </ErrorBoundary>
  );
}
```

## Performance Optimization

### Static Generation

- All pages use Static Generation (SSG)
- `generateStaticParams()` pre-renders popular routes
- Build-time data fetching for better performance

### Loading States

- Skeleton loaders prevent layout shift
- Progressive loading for better perceived performance
- Error boundaries prevent full-page crashes

### Image Optimization

- Images set to `unoptimized: true` for static export
- Consider using CDN for production images

## Browser Support

- Chrome/Edge (latest 2 versions)
- Firefox (latest 2 versions)
- Safari (latest 2 versions)
- No IE11 support

## Troubleshooting

### Build Failures

**Issue**: TypeScript errors during build
```bash
# Clear cache and rebuild
rm -rf .next
npm run build
```

**Issue**: API 503 errors during build
- This is normal - API rate limits during static generation
- Build will succeed, some pages may have stale data
- Solution: Implement retry logic or reduce parallelism

### Runtime Errors

**Issue**: Blank pages in production
- Check browser console for errors
- Verify API endpoints are accessible
- Check CORS configuration

**Issue**: "Cannot find module" errors
- Run `npm install`
- Check import paths use `@/` alias

## Contributing

### Code Style

- Use TypeScript for all new files
- Follow ESLint rules: `npm run lint`
- Use Prettier for formatting (automatic on save)
- Write tests for new features

### Commit Conventions

```
feat: Add new feature
fix: Bug fix
docs: Documentation changes
test: Test changes
chore: Build/config changes
```

### Pull Request Process

1. Create feature branch: `git checkout -b feature/my-feature`
2. Make changes and add tests
3. Run tests: `npm test`
4. Build: `npm run build`
5. Commit and push
6. Create PR to `main` branch

## License

MIT License - see LICENSE file for details

## Support

- **Issues**: https://github.com/Jakeintech/congress-disclosures-standardized/issues
- **Discussions**: https://github.com/Jakeintech/congress-disclosures-standardized/discussions
- **API Docs**: See `docs/API_ENDPOINTS.md`

## Roadmap

- [x] Error boundaries on all pages
- [x] Comprehensive API testing
- [x] Vercel deployment configuration
- [ ] Component unit tests
- [ ] E2E tests with Playwright
- [ ] Dark mode support
- [ ] Advanced filtering
- [ ] Data export functionality
- [ ] Real-time updates
- [ ] Mobile app (React Native)

## Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [shadcn/ui Components](https://ui.shadcn.com)
- [React Testing Library](https://testing-library.com/react)
- [Vercel Deployment](https://vercel.com/docs)
