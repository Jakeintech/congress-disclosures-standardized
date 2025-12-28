import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Code, Key, Zap, AlertTriangle, TrendingUp } from 'lucide-react';
import Link from 'next/link';

export const metadata = {
  title: 'API Terms of Service - Congress Activity Platform',
  description: 'Terms and conditions for API access and usage',
};

export default function APITermsPage() {
  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
          <Code className="h-8 w-8" />
          API Terms of Service
        </h1>
        <p className="text-muted-foreground mt-2">
          Last Updated: December 11, 2025
        </p>
      </div>

      {/* Introduction */}
      <Card>
        <CardHeader>
          <CardTitle>API Access Agreement</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <p className="text-muted-foreground">
            These API Terms of Service ("API Terms") govern your access to and use of the Congress Activity
            Platform API (the "API"). By accessing or using the API, you agree to be bound by these API Terms
            and our general <Link href="/legal/terms" className="text-primary hover:underline">Terms of Service</Link>.
          </p>
          <p className="text-muted-foreground">
            If there is any conflict between these API Terms and the general Terms of Service, these API Terms
            shall take precedence for API-specific matters.
          </p>
        </CardContent>
      </Card>

      {/* API Access Tiers */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            1. API Access Tiers
          </CardTitle>
          <CardDescription>Rate limits and features by tier</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          {/* Free Tier */}
          <div className="border rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-semibold text-base">Free Tier</h4>
              <span className="text-xs bg-primary/10 text-primary px-2 py-1 rounded">Default</span>
            </div>
            <ul className="list-disc list-inside space-y-1 ml-4 text-muted-foreground">
              <li><strong>Rate Limit:</strong> 100 requests per hour</li>
              <li><strong>Daily Limit:</strong> 1,000 requests per day</li>
              <li><strong>Burst Limit:</strong> 10 requests per second</li>
              <li><strong>Features:</strong> Access to all public endpoints</li>
              <li><strong>Use Case:</strong> Personal projects, research, civic applications</li>
              <li><strong>Authentication:</strong> Optional API key (recommended for tracking)</li>
            </ul>
          </div>

          {/* Pro Tier */}
          <div className="border rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-semibold text-base">Pro Tier</h4>
              <span className="text-xs bg-muted text-muted-foreground px-2 py-1 rounded">Coming Soon</span>
            </div>
            <ul className="list-disc list-inside space-y-1 ml-4 text-muted-foreground">
              <li><strong>Rate Limit:</strong> 1,000 requests per hour</li>
              <li><strong>Daily Limit:</strong> 10,000 requests per day</li>
              <li><strong>Burst Limit:</strong> 50 requests per second</li>
              <li><strong>Features:</strong> Priority support, webhook notifications, batch endpoints</li>
              <li><strong>Use Case:</strong> News organizations, academic institutions, non-profits</li>
              <li><strong>Authentication:</strong> Required API key with enhanced security</li>
            </ul>
          </div>

          {/* Enterprise Tier */}
          <div className="border rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-semibold text-base">Enterprise Tier</h4>
              <span className="text-xs bg-muted text-muted-foreground px-2 py-1 rounded">Contact Us</span>
            </div>
            <ul className="list-disc list-inside space-y-1 ml-4 text-muted-foreground">
              <li><strong>Rate Limit:</strong> Custom (negotiable)</li>
              <li><strong>Daily Limit:</strong> Custom (negotiable)</li>
              <li><strong>Burst Limit:</strong> Custom (negotiable)</li>
              <li><strong>Features:</strong> Dedicated support, SLA guarantees, custom endpoints, on-premise options</li>
              <li><strong>Use Case:</strong> Large-scale research institutions, government agencies</li>
              <li><strong>Authentication:</strong> OAuth 2.0 + API keys</li>
            </ul>
          </div>

          <Alert>
            <AlertDescription className="text-sm">
              <strong>Current Status:</strong> All tiers are currently free during beta. Pro and Enterprise
              tiers will be introduced in Q2 2026 with at least 60 days advance notice.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>

      {/* API Key Management */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Key className="h-5 w-5" />
            2. API Key Management
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <div>
            <h4 className="font-semibold mb-2">2.1 Obtaining an API Key</h4>
            <p className="text-muted-foreground mb-2">
              API keys are currently optional but recommended for tracking and rate limit monitoring.
              To request an API key:
            </p>
            <ul className="list-disc list-inside space-y-1 ml-4 text-muted-foreground">
              <li>Submit a request through our <a href="https://github.com/Jakeintech/congress-disclosures-standardized/issues" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">GitHub repository</a></li>
              <li>Provide your email address and intended use case</li>
              <li>Receive your API key via email within 24-48 hours</li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold mb-2">2.2 API Key Security</h4>
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                <strong>Security Requirements:</strong>
              </AlertDescription>
            </Alert>
            <ul className="list-disc list-inside space-y-1 ml-4 text-muted-foreground mt-2">
              <li>Keep your API key confidential - do not share or expose it publicly</li>
              <li>Never commit API keys to version control (GitHub, GitLab, etc.)</li>
              <li>Use environment variables or secure key management systems</li>
              <li>Rotate keys immediately if compromised</li>
              <li>Use separate keys for development and production environments</li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold mb-2">2.3 Key Revocation</h4>
            <p className="text-muted-foreground">
              We reserve the right to revoke API keys at any time for violations of these API Terms,
              including but not limited to: abuse, excessive use, prohibited commercial use, or security concerns.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Rate Limiting */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5" />
            3. Rate Limiting & Throttling
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <div>
            <h4 className="font-semibold mb-2">3.1 Rate Limit Enforcement</h4>
            <p className="text-muted-foreground mb-2">
              Rate limits are enforced using a sliding window algorithm. When you exceed your rate limit,
              you will receive a <code className="bg-muted px-1 py-0.5 rounded">429 Too Many Requests</code> response.
            </p>
            <div className="bg-muted p-3 rounded-md font-mono text-xs mt-2">
              <pre>{`{
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded. Retry after 3600 seconds.",
  "retry_after": 3600,
  "limit": 100,
  "remaining": 0,
  "reset": 1735689600
}`}</pre>
            </div>
          </div>

          <div>
            <h4 className="font-semibold mb-2">3.2 Rate Limit Headers</h4>
            <p className="text-muted-foreground mb-2">All API responses include rate limit headers:</p>
            <ul className="list-disc list-inside space-y-1 ml-4 text-muted-foreground">
              <li><code className="bg-muted px-1 py-0.5 rounded">X-RateLimit-Limit</code>: Total requests allowed per hour</li>
              <li><code className="bg-muted px-1 py-0.5 rounded">X-RateLimit-Remaining</code>: Requests remaining in current window</li>
              <li><code className="bg-muted px-1 py-0.5 rounded">X-RateLimit-Reset</code>: Unix timestamp when limit resets</li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold mb-2">3.3 Best Practices</h4>
            <ul className="list-disc list-inside space-y-1 ml-4 text-muted-foreground">
              <li>Implement exponential backoff for 429 responses</li>
              <li>Cache responses locally when possible</li>
              <li>Use pagination parameters to reduce response sizes</li>
              <li>Monitor rate limit headers to avoid hitting limits</li>
              <li>Batch requests when supported by the endpoint</li>
            </ul>
          </div>
        </CardContent>
      </Card>

      {/* Acceptable Use */}
      <Card>
        <CardHeader>
          <CardTitle>4. API Acceptable Use Policy</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <div>
            <h4 className="font-semibold mb-2">4.1 Permitted API Uses</h4>
            <ul className="list-disc list-inside space-y-1 ml-4 text-muted-foreground">
              <li>Building transparency and accountability applications</li>
              <li>Academic research and statistical analysis</li>
              <li>News and media reporting</li>
              <li>Civic engagement and education platforms</li>
              <li>Non-commercial data visualizations and dashboards</li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold mb-2">4.2 Prohibited API Uses</h4>
            <Alert variant="destructive" className="mb-2">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                The following uses violate these API Terms and may result in immediate key revocation:
              </AlertDescription>
            </Alert>
            <ul className="list-disc list-inside space-y-1 ml-4 text-muted-foreground">
              <li>Commercial solicitation or marketing (except news/media organizations)</li>
              <li>Credit rating determination or creditworthiness assessment</li>
              <li>Reselling or redistributing API data for profit</li>
              <li>Scraping or automated data harvesting beyond API limits</li>
              <li>Circumventing rate limits or security measures</li>
              <li>Reverse engineering or decompiling the API</li>
              <li>Using the API to harass, defame, or harm individuals</li>
              <li>Violating any applicable laws or regulations</li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold mb-2">4.3 Commercial Use Restrictions</h4>
            <p className="text-muted-foreground">
              Commercial use of the API requires explicit written authorization. "Commercial use" includes:
            </p>
            <ul className="list-disc list-inside space-y-1 ml-4 text-muted-foreground mt-2">
              <li>Selling access to API data or derivative products</li>
              <li>Incorporating API data into commercial software as a service (SaaS) products</li>
              <li>Using API data for lead generation or customer prospecting</li>
              <li>Any use where API data is a core component of a revenue-generating product</li>
            </ul>
            <p className="text-muted-foreground mt-2">
              Exception: News organizations, journalists, and media companies may use the API for commercial
              reporting purposes without additional authorization.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Attribution */}
      <Card>
        <CardHeader>
          <CardTitle>5. Attribution Requirements</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <div>
            <h4 className="font-semibold mb-2">5.1 Required Attribution</h4>
            <p className="text-muted-foreground mb-2">
              When displaying data from the API, you must provide clear attribution:
            </p>
            <div className="bg-muted p-3 rounded-md mt-2">
              <p className="font-semibold mb-1">Minimum Attribution Text:</p>
              <p className="text-muted-foreground">
                "Data provided by the <a href="https://congress-transparency.example.com" className="text-primary hover:underline">Congress Activity Platform</a>,
                sourced from official congressional financial disclosures."
              </p>
            </div>
          </div>

          <div>
            <h4 className="font-semibold mb-2">5.2 Source Attribution</h4>
            <p className="text-muted-foreground">
              You must also acknowledge the original data sources:
            </p>
            <ul className="list-disc list-inside space-y-1 ml-4 text-muted-foreground mt-2">
              <li>U.S. House of Representatives Clerk's Office</li>
              <li>U.S. Senate Select Committee on Ethics</li>
              <li>Congress.gov (Library of Congress)</li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold mb-2">5.3 Logo Usage</h4>
            <p className="text-muted-foreground">
              You may use the Congress Activity Platform logo in connection with attribution.
              Do not modify, distort, or alter the logo. Do not imply endorsement or partnership
              without written permission.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Data Caching */}
      <Card>
        <CardHeader>
          <CardTitle>6. Data Caching and Storage</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <div>
            <h4 className="font-semibold mb-2">6.1 Permitted Caching</h4>
            <p className="text-muted-foreground mb-2">You may cache API responses for reasonable periods:</p>
            <ul className="list-disc list-inside space-y-1 ml-4 text-muted-foreground">
              <li><strong>Member Data:</strong> Cache up to 7 days</li>
              <li><strong>Transaction Data:</strong> Cache up to 24 hours</li>
              <li><strong>Bill/Committee Data:</strong> Cache up to 7 days</li>
              <li><strong>Analytics/Aggregates:</strong> Cache up to 1 hour</li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold mb-2">6.2 Cache Invalidation</h4>
            <p className="text-muted-foreground">
              Implement cache invalidation based on API response headers (<code className="bg-muted px-1 py-0.5 rounded">Cache-Control</code>,
              <code className="bg-muted px-1 py-0.5 rounded">ETag</code>). Respect <code className="bg-muted px-1 py-0.5 rounded">max-age</code> directives.
            </p>
          </div>

          <div>
            <h4 className="font-semibold mb-2">6.3 Long-Term Storage</h4>
            <Alert>
              <AlertDescription className="text-sm">
                <strong>Bulk Downloads:</strong> For long-term storage or bulk analysis, use our
                Parquet data exports (coming soon) instead of caching API responses. Contact us for
                access to historical data dumps.
              </AlertDescription>
            </Alert>
          </div>
        </CardContent>
      </Card>

      {/* API Changes */}
      <Card>
        <CardHeader>
          <CardTitle>7. API Changes and Deprecation</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <div>
            <h4 className="font-semibold mb-2">7.1 Versioning</h4>
            <p className="text-muted-foreground mb-2">
              The API uses URL-based versioning (e.g., <code className="bg-muted px-1 py-0.5 rounded">/v1/</code>,
              <code className="bg-muted px-1 py-0.5 rounded">/v2/</code>). We will maintain support for
              previous versions for at least 12 months after a new version is released.
            </p>
          </div>

          <div>
            <h4 className="font-semibold mb-2">7.2 Breaking Changes</h4>
            <p className="text-muted-foreground mb-2">
              Breaking changes will only be introduced in new API versions. Examples of breaking changes:
            </p>
            <ul className="list-disc list-inside space-y-1 ml-4 text-muted-foreground">
              <li>Removing or renaming fields</li>
              <li>Changing field data types</li>
              <li>Removing endpoints</li>
              <li>Changing authentication mechanisms</li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold mb-2">7.3 Non-Breaking Changes</h4>
            <p className="text-muted-foreground mb-2">
              Non-breaking changes may be introduced without version changes:
            </p>
            <ul className="list-disc list-inside space-y-1 ml-4 text-muted-foreground">
              <li>Adding new endpoints</li>
              <li>Adding new optional request parameters</li>
              <li>Adding new fields to responses</li>
              <li>Changing error message text</li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold mb-2">7.4 Deprecation Process</h4>
            <p className="text-muted-foreground">
              When deprecating endpoints or versions:
            </p>
            <ul className="list-disc list-inside space-y-1 ml-4 text-muted-foreground mt-2">
              <li>90-day advance notice via email (for registered API key holders)</li>
              <li>Deprecation warnings in API responses via <code className="bg-muted px-1 py-0.5 rounded">Sunset</code> header</li>
              <li>Documentation updates with migration guides</li>
              <li>12-month support period before final removal</li>
            </ul>
          </div>
        </CardContent>
      </Card>

      {/* Support and SLA */}
      <Card>
        <CardHeader>
          <CardTitle>8. Support and Service Level</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <div>
            <h4 className="font-semibold mb-2">8.1 API Uptime</h4>
            <p className="text-muted-foreground">
              We strive for 99.5% uptime but make no guarantees during the beta period. Service Level
              Agreements (SLAs) will be available for Pro and Enterprise tiers.
            </p>
          </div>

          <div>
            <h4 className="font-semibold mb-2">8.2 Support Channels</h4>
            <ul className="list-disc list-inside space-y-1 ml-4 text-muted-foreground">
              <li><strong>Free Tier:</strong> Community support via GitHub Issues</li>
              <li><strong>Pro Tier:</strong> Email support (24-48 hour response time)</li>
              <li><strong>Enterprise Tier:</strong> Dedicated support (4-hour response time, 24/7 emergency contact)</li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold mb-2">8.3 Status Page</h4>
            <p className="text-muted-foreground">
              Monitor API status and scheduled maintenance at <Link href="/status" className="text-primary hover:underline">status.congress-transparency.example.com</Link> (coming soon).
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Liability */}
      <Card>
        <CardHeader>
          <CardTitle>9. Liability and Warranties</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <div>
            <h4 className="font-semibold mb-2">9.1 No Warranties</h4>
            <p className="text-muted-foreground">
              THE API IS PROVIDED "AS IS" WITHOUT WARRANTIES OF ANY KIND. WE DO NOT GUARANTEE
              ACCURACY, COMPLETENESS, OR AVAILABILITY OF API DATA.
            </p>
          </div>

          <div>
            <h4 className="font-semibold mb-2">9.2 Limitation of Liability</h4>
            <p className="text-muted-foreground">
              WE SHALL NOT BE LIABLE FOR ANY DAMAGES ARISING FROM API USE, INCLUDING BUT NOT LIMITED TO
              LOSS OF DATA, LOSS OF PROFITS, OR BUSINESS INTERRUPTION.
            </p>
          </div>

          <div>
            <h4 className="font-semibold mb-2">9.3 Indemnification</h4>
            <p className="text-muted-foreground">
              You agree to indemnify and hold us harmless from any claims arising from your use of the API
              or violation of these API Terms.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Termination */}
      <Card>
        <CardHeader>
          <CardTitle>10. Termination</CardTitle>
        </CardHeader>
        <CardContent className="text-sm space-y-4">
          <p className="text-muted-foreground">
            We may suspend or terminate your API access immediately without notice if:
          </p>
          <ul className="list-disc list-inside space-y-1 ml-4 text-muted-foreground">
            <li>You violate these API Terms or our Terms of Service</li>
            <li>Your use poses a security risk or disrupts the API</li>
            <li>You engage in prohibited commercial use without authorization</li>
            <li>You provide false information or misrepresent your identity</li>
          </ul>
          <p className="text-muted-foreground mt-4">
            Upon termination, you must immediately stop using the API and delete all cached data
            obtained through the API.
          </p>
        </CardContent>
      </Card>

      {/* Contact */}
      <Card>
        <CardHeader>
          <CardTitle>11. Contact and Questions</CardTitle>
        </CardHeader>
        <CardContent className="text-sm">
          <p className="text-muted-foreground">
            For API-related questions, documentation, or to request higher rate limits, contact us through our{' '}
            <a href="https://github.com/Jakeintech/congress-disclosures-standardized/issues"
               target="_blank"
               rel="noopener noreferrer"
               className="text-primary hover:underline">
              GitHub repository
            </a>.
          </p>
        </CardContent>
      </Card>

      {/* Footer Navigation */}
      <div className="flex gap-4 pt-6 border-t">
        <Link href="/legal/basis" className="text-sm text-primary hover:underline">
          ← Legal Basis
        </Link>
        <Link href="/legal/terms" className="text-sm text-primary hover:underline">
          Terms of Service
        </Link>
        <Link href="/legal/privacy" className="text-sm text-primary hover:underline">
          Privacy Policy
        </Link>
      </div>
    </div>
  );
}
