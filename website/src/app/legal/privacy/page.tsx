import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Shield, Eye, Cookie, Database, Lock } from 'lucide-react';
import Link from 'next/link';

export const metadata = {
  title: 'Privacy Policy - Congress Transparency Platform',
  description: 'How we collect, use, and protect your information',
};

export default function PrivacyPage() {
  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
          <Shield className="h-8 w-8" />
          Privacy Policy
        </h1>
        <p className="text-muted-foreground mt-2">
          Last Updated: December 11, 2025
        </p>
      </div>

      {/* Key Principles */}
      <Alert>
        <Eye className="h-4 w-4" />
        <AlertDescription>
          <strong>Privacy-First Approach:</strong> This Platform is designed to minimize data collection.
          We do not require user accounts, and we do not sell or share personal information.
        </AlertDescription>
      </Alert>

      {/* Introduction */}
      <Card>
        <CardHeader>
          <CardTitle>Our Commitment to Privacy</CardTitle>
        </CardHeader>
        <CardContent className="text-sm space-y-4">
          <p className="text-muted-foreground">
            The Congress Transparency Platform ("Platform", "we", "us", or "our") is committed to protecting
            your privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard your
            information when you visit our Platform.
          </p>
          <p className="text-muted-foreground">
            By using the Platform, you consent to the data practices described in this policy.
          </p>
        </CardContent>
      </Card>

      {/* Information We Collect */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="h-5 w-5" />
            1. Information We Collect
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <div>
            <h4 className="font-semibold mb-2">1.1 Automatically Collected Information</h4>
            <p className="text-muted-foreground mb-2">
              When you visit the Platform, we may automatically collect certain information, including:
            </p>
            <ul className="list-disc list-inside space-y-1 ml-4 text-muted-foreground">
              <li><strong>Server Logs:</strong> IP address, browser type, device information, operating system</li>
              <li><strong>Usage Data:</strong> Pages visited, time spent, referring URLs, clickstream data</li>
              <li><strong>API Requests:</strong> Endpoint accessed, query parameters (for rate limiting and abuse prevention)</li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold mb-2">1.2 Information You Provide</h4>
            <p className="text-muted-foreground mb-2">
              We collect information you voluntarily provide when using certain features:
            </p>
            <ul className="list-disc list-inside space-y-1 ml-4 text-muted-foreground">
              <li><strong>API Keys:</strong> Email address (optional) if you request an API key</li>
              <li><strong>Feedback:</strong> Information submitted through GitHub Issues</li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold mb-2">1.3 Information We Do NOT Collect</h4>
            <Alert>
              <AlertDescription className="text-sm">
                We do not require user accounts, we do not collect names, addresses, phone numbers,
                financial information, or any other personally identifiable information unless you
                voluntarily provide it (e.g., via GitHub).
              </AlertDescription>
            </Alert>
          </div>
        </CardContent>
      </Card>

      {/* How We Use Information */}
      <Card>
        <CardHeader>
          <CardTitle>2. How We Use Your Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <p className="text-muted-foreground mb-2">We use collected information for the following purposes:</p>
          <ul className="list-disc list-inside space-y-2 ml-4 text-muted-foreground">
            <li>
              <strong>Platform Operation:</strong> To provide, maintain, and improve the Platform's functionality
            </li>
            <li>
              <strong>Security & Abuse Prevention:</strong> To detect and prevent unauthorized access,
              API abuse, or violations of our Terms of Service
            </li>
            <li>
              <strong>Performance Monitoring:</strong> To analyze usage patterns and optimize Platform performance
            </li>
            <li>
              <strong>Rate Limiting:</strong> To enforce API rate limits and prevent system overload
            </li>
            <li>
              <strong>Legal Compliance:</strong> To comply with applicable laws and legal processes
            </li>
          </ul>
        </CardContent>
      </Card>

      {/* Cookies and Tracking */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Cookie className="h-5 w-5" />
            3. Cookies and Tracking Technologies
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <div>
            <h4 className="font-semibold mb-2">3.1 First-Party Cookies</h4>
            <p className="text-muted-foreground mb-2">
              We use essential cookies and local storage for:
            </p>
            <ul className="list-disc list-inside space-y-1 ml-4 text-muted-foreground">
              <li>Theme preferences (dark/light mode)</li>
              <li>User interface settings</li>
              <li>API authentication tokens (if using API features)</li>
            </ul>
            <p className="text-muted-foreground mt-2">
              These are strictly necessary for Platform functionality and do not track you across websites.
            </p>
          </div>

          <div>
            <h4 className="font-semibold mb-2">3.2 Third-Party Analytics</h4>
            <Alert>
              <AlertDescription className="text-sm">
                <strong>Current Status:</strong> We currently do NOT use third-party analytics services
                (Google Analytics, etc.). If this changes in the future, we will update this policy and
                provide opt-out mechanisms.
              </AlertDescription>
            </Alert>
          </div>

          <div>
            <h4 className="font-semibold mb-2">3.3 Do Not Track (DNT)</h4>
            <p className="text-muted-foreground">
              Since we do not track users across websites, DNT signals are not applicable. We respect
              your browser's privacy settings.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Data Sharing */}
      <Card>
        <CardHeader>
          <CardTitle>4. How We Share Your Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <Alert>
            <AlertDescription>
              <strong>We do not sell, rent, or trade your personal information to third parties.</strong>
            </AlertDescription>
          </Alert>

          <div>
            <p className="text-muted-foreground mb-2">We may share information only in these limited circumstances:</p>
            <ul className="list-disc list-inside space-y-2 ml-4 text-muted-foreground">
              <li>
                <strong>Service Providers:</strong> AWS (for hosting), Vercel (for deployment) - only to the
                extent necessary to operate the Platform
              </li>
              <li>
                <strong>Legal Requirements:</strong> If required by law, subpoena, or legal process
              </li>
              <li>
                <strong>Security & Fraud Prevention:</strong> To investigate abuse, violations, or security threats
              </li>
              <li>
                <strong>Open Source Community:</strong> Aggregated, anonymized usage statistics may be shared
                with the open-source community
              </li>
            </ul>
          </div>
        </CardContent>
      </Card>

      {/* Data Security */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Lock className="h-5 w-5" />
            5. Data Security
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <p className="text-muted-foreground">
            We implement reasonable security measures to protect information from unauthorized access,
            alteration, disclosure, or destruction:
          </p>
          <ul className="list-disc list-inside space-y-1 ml-4 text-muted-foreground">
            <li>HTTPS encryption for all data transmission</li>
            <li>AWS security best practices (IAM roles, encryption at rest)</li>
            <li>Regular security audits of open-source codebase</li>
            <li>Rate limiting and abuse detection systems</li>
          </ul>
          <Alert variant="destructive" className="mt-4">
            <AlertDescription className="text-sm">
              <strong>Important:</strong> No method of transmission over the Internet or electronic storage
              is 100% secure. While we strive to protect your information, we cannot guarantee absolute security.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>

      {/* Data Retention */}
      <Card>
        <CardHeader>
          <CardTitle>6. Data Retention</CardTitle>
        </CardHeader>
        <CardContent className="text-sm space-y-4">
          <ul className="list-disc list-inside space-y-2 ml-4 text-muted-foreground">
            <li>
              <strong>Server Logs:</strong> Retained for 30 days for security and debugging purposes
            </li>
            <li>
              <strong>API Request Logs:</strong> Retained for 90 days for rate limiting and abuse prevention
            </li>
            <li>
              <strong>User Preferences:</strong> Stored in browser local storage indefinitely (you can clear at any time)
            </li>
          </ul>
        </CardContent>
      </Card>

      {/* Your Rights */}
      <Card>
        <CardHeader>
          <CardTitle>7. Your Privacy Rights</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <p className="text-muted-foreground">You have the right to:</p>
          <ul className="list-disc list-inside space-y-1 ml-4 text-muted-foreground">
            <li><strong>Access:</strong> Request a copy of information we have about you</li>
            <li><strong>Correction:</strong> Request correction of inaccurate information</li>
            <li><strong>Deletion:</strong> Request deletion of your information (subject to legal retention requirements)</li>
            <li><strong>Opt-Out:</strong> Stop using the Platform at any time</li>
            <li><strong>Portability:</strong> Request your data in a portable format</li>
          </ul>
          <p className="text-muted-foreground mt-4">
            To exercise these rights, contact us through our{' '}
            <a href="https://github.com/Jakeintech/congress-disclosures-standardized/issues"
               target="_blank"
               rel="noopener noreferrer"
               className="text-primary hover:underline">
              GitHub repository
            </a>.
          </p>
        </CardContent>
      </Card>

      {/* Children's Privacy */}
      <Card>
        <CardHeader>
          <CardTitle>8. Children's Privacy</CardTitle>
        </CardHeader>
        <CardContent className="text-sm">
          <p className="text-muted-foreground">
            This Platform is not directed to children under 13. We do not knowingly collect personal
            information from children. If you believe we have inadvertently collected information from a
            child, please contact us immediately.
          </p>
        </CardContent>
      </Card>

      {/* International Users */}
      <Card>
        <CardHeader>
          <CardTitle>9. International Users</CardTitle>
        </CardHeader>
        <CardContent className="text-sm">
          <p className="text-muted-foreground">
            This Platform is hosted in the United States and governed by U.S. law. If you access the Platform
            from outside the U.S., your information may be transferred to, stored, and processed in the U.S.
            By using the Platform, you consent to this transfer.
          </p>
        </CardContent>
      </Card>

      {/* Changes to Policy */}
      <Card>
        <CardHeader>
          <CardTitle>10. Changes to This Privacy Policy</CardTitle>
        </CardHeader>
        <CardContent className="text-sm">
          <p className="text-muted-foreground">
            We may update this Privacy Policy from time to time. Changes will be effective immediately upon
            posting. The "Last Updated" date indicates when the policy was last revised. Your continued use
            after changes constitutes acceptance of the updated policy.
          </p>
        </CardContent>
      </Card>

      {/* Contact */}
      <Card>
        <CardHeader>
          <CardTitle>11. Contact Us</CardTitle>
        </CardHeader>
        <CardContent className="text-sm">
          <p className="text-muted-foreground">
            For privacy-related questions or concerns, please contact us through our{' '}
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
        <Link href="/legal/api-terms" className="text-sm text-primary hover:underline">
          API Terms →
        </Link>
      </div>
    </div>
  );
}
