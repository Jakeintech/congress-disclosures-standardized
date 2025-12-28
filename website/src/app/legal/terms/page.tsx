import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { FileText, AlertTriangle } from 'lucide-react';
import Link from 'next/link';

export const metadata = {
  title: 'Terms of Service - Congress Activity Platform',
  description: 'Terms and conditions for using the Congress Activity Platform',
};

export default function TermsPage() {
  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
          <FileText className="h-8 w-8" />
          Terms of Service
        </h1>
        <p className="text-muted-foreground mt-2">
          Last Updated: December 11, 2025
        </p>
      </div>

      {/* Introduction */}
      <Card>
        <CardHeader>
          <CardTitle>Agreement to Terms</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <p>
            Welcome to the <strong>Congress Activity Platform</strong> (the "Platform", "Service", "we", "us", or "our").
            By accessing or using this Platform, you agree to be bound by these Terms of Service ("Terms").
          </p>
          <p>
            If you do not agree to these Terms, please do not use the Platform.
          </p>
        </CardContent>
      </Card>

      {/* Use of Service */}
      <Card>
        <CardHeader>
          <CardTitle>1. Use of Service</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <div>
            <h4 className="font-semibold mb-2">1.1 Permitted Uses</h4>
            <p className="text-muted-foreground mb-2">You may use this Platform for:</p>
            <ul className="list-disc list-inside space-y-1 ml-4 text-muted-foreground">
              <li>Research and analysis of congressional financial disclosures</li>
              <li>Educational purposes and civic engagement</li>
              <li>Journalism and public interest reporting</li>
              <li>Academic study and statistical analysis</li>
              <li>Personal transparency monitoring</li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold mb-2">1.2 Prohibited Uses</h4>
            <Alert variant="destructive" className="mb-2">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                The following uses are expressly prohibited per 5 U.S.C. § 13107:
              </AlertDescription>
            </Alert>
            <ul className="list-disc list-inside space-y-1 ml-4 text-muted-foreground">
              <li>Commercial solicitation or marketing purposes</li>
              <li>Credit rating determination or creditworthiness assessment</li>
              <li>Fundraising campaigns or donor solicitation</li>
              <li>Creating marketing lists or lead generation databases</li>
              <li>Any use that violates federal or state law</li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold mb-2">1.3 User Conduct</h4>
            <p className="text-muted-foreground mb-2">You agree NOT to:</p>
            <ul className="list-disc list-inside space-y-1 ml-4 text-muted-foreground">
              <li>Attempt to gain unauthorized access to the Platform or its systems</li>
              <li>Scrape, harvest, or collect data using automated means without permission</li>
              <li>Disrupt or interfere with the Platform's operation</li>
              <li>Misrepresent your identity or affiliation</li>
              <li>Use the Platform for any illegal purpose</li>
            </ul>
          </div>
        </CardContent>
      </Card>

      {/* Data and Content */}
      <Card>
        <CardHeader>
          <CardTitle>2. Data and Content</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <div>
            <h4 className="font-semibold mb-2">2.1 Data Sources</h4>
            <p className="text-muted-foreground">
              All financial disclosure data is sourced from official public records maintained by:
            </p>
            <ul className="list-disc list-inside space-y-1 ml-4 text-muted-foreground mt-2">
              <li>U.S. House of Representatives Clerk's Office</li>
              <li>U.S. Senate Select Committee on Ethics</li>
              <li>Congress.gov (Library of Congress)</li>
              <li>Senate Lobbying Disclosure Database</li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold mb-2">2.2 Data Accuracy</h4>
            <p className="text-muted-foreground">
              While we strive for accuracy, this Platform provides data "as is" without warranties of any kind.
              We do not guarantee the completeness, accuracy, or timeliness of the information provided.
              Users should verify critical information with official government sources.
            </p>
          </div>

          <div>
            <h4 className="font-semibold mb-2">2.3 Intellectual Property</h4>
            <p className="text-muted-foreground">
              The Platform's code is open-source under the MIT License. Financial disclosure data is
              public domain per federal law. Analysis, visualizations, and aggregations created by this
              Platform are available under Creative Commons Attribution 4.0 International (CC BY 4.0).
            </p>
          </div>
        </CardContent>
      </Card>

      {/* API Terms */}
      <Card>
        <CardHeader>
          <CardTitle>3. API Access</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <p className="text-muted-foreground">
            API access is subject to additional terms. See our <Link href="/legal/api-terms" className="text-primary hover:underline">API Terms of Service</Link> for details.
          </p>
          <ul className="list-disc list-inside space-y-1 ml-4 text-muted-foreground">
            <li>Rate limits apply to all API endpoints</li>
            <li>API keys may be revoked for abuse or violations</li>
            <li>Commercial API use requires prior authorization</li>
          </ul>
        </CardContent>
      </Card>

      {/* Disclaimers */}
      <Card>
        <CardHeader>
          <CardTitle>4. Disclaimers and Limitations</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <div>
            <h4 className="font-semibold mb-2">4.1 No Warranties</h4>
            <p className="text-muted-foreground">
              THIS PLATFORM IS PROVIDED "AS IS" AND "AS AVAILABLE" WITHOUT WARRANTIES OF ANY KIND,
              EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO IMPLIED WARRANTIES OF MERCHANTABILITY,
              FITNESS FOR A PARTICULAR PURPOSE, OR NON-INFRINGEMENT.
            </p>
          </div>

          <div>
            <h4 className="font-semibold mb-2">4.2 Limitation of Liability</h4>
            <p className="text-muted-foreground">
              IN NO EVENT SHALL THE PLATFORM OPERATORS BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL,
              CONSEQUENTIAL, OR PUNITIVE DAMAGES ARISING OUT OF OR RELATED TO YOUR USE OF THE PLATFORM.
            </p>
          </div>

          <div>
            <h4 className="font-semibold mb-2">4.3 Not Legal Advice</h4>
            <p className="text-muted-foreground">
              Information provided by this Platform does not constitute legal, financial, or investment advice.
              Consult qualified professionals for specific guidance.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Privacy */}
      <Card>
        <CardHeader>
          <CardTitle>5. Privacy</CardTitle>
        </CardHeader>
        <CardContent className="text-sm">
          <p className="text-muted-foreground">
            Your use of the Platform is also governed by our <Link href="/legal/privacy" className="text-primary hover:underline">Privacy Policy</Link>,
            which is incorporated into these Terms by reference.
          </p>
        </CardContent>
      </Card>

      {/* Changes to Terms */}
      <Card>
        <CardHeader>
          <CardTitle>6. Changes to Terms</CardTitle>
        </CardHeader>
        <CardContent className="text-sm">
          <p className="text-muted-foreground">
            We reserve the right to modify these Terms at any time. Changes will be effective immediately
            upon posting to this page. Your continued use of the Platform after changes constitutes acceptance
            of the modified Terms. The "Last Updated" date at the top reflects the most recent changes.
          </p>
        </CardContent>
      </Card>

      {/* Termination */}
      <Card>
        <CardHeader>
          <CardTitle>7. Termination</CardTitle>
        </CardHeader>
        <CardContent className="text-sm">
          <p className="text-muted-foreground">
            We may terminate or suspend your access to the Platform at any time, without prior notice,
            for conduct that we believe violates these Terms or is harmful to other users, us, or third parties,
            or for any other reason in our sole discretion.
          </p>
        </CardContent>
      </Card>

      {/* Governing Law */}
      <Card>
        <CardHeader>
          <CardTitle>8. Governing Law and Jurisdiction</CardTitle>
        </CardHeader>
        <CardContent className="text-sm">
          <p className="text-muted-foreground">
            These Terms shall be governed by and construed in accordance with the laws of the United States
            and the District of Columbia, without regard to conflict of law provisions. Any disputes arising
            under these Terms shall be subject to the exclusive jurisdiction of the federal and state courts
            located in the District of Columbia.
          </p>
        </CardContent>
      </Card>

      {/* Contact */}
      <Card>
        <CardHeader>
          <CardTitle>9. Contact Information</CardTitle>
        </CardHeader>
        <CardContent className="text-sm">
          <p className="text-muted-foreground">
            For questions about these Terms, please contact us through our{' '}
            <a href="https://github.com/Jakeintech/congress-disclosures-standardized/issues"
               target="_blank"
               rel="noopener noreferrer"
               className="text-primary hover:underline">
              GitHub repository
            </a>.
          </p>
        </CardContent>
      </Card>

      {/* Severability */}
      <Card>
        <CardHeader>
          <CardTitle>10. Severability</CardTitle>
        </CardHeader>
        <CardContent className="text-sm">
          <p className="text-muted-foreground">
            If any provision of these Terms is found to be unenforceable or invalid, that provision shall be
            limited or eliminated to the minimum extent necessary, and the remaining provisions shall remain
            in full force and effect.
          </p>
        </CardContent>
      </Card>

      {/* Footer Navigation */}
      <div className="flex gap-4 pt-6 border-t">
        <Link href="/legal/basis" className="text-sm text-primary hover:underline">
          ← Legal Basis
        </Link>
        <Link href="/legal/privacy" className="text-sm text-primary hover:underline">
          Privacy Policy →
        </Link>
        <Link href="/legal/api-terms" className="text-sm text-primary hover:underline">
          API Terms →
        </Link>
      </div>
    </div>
  );
}
