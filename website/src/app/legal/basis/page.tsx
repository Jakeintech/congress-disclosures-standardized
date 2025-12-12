import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Scale, FileText, ExternalLink } from 'lucide-react';
import Link from 'next/link';

export const metadata = {
  title: 'Legal Basis - Congress Transparency Platform',
  description: 'Legal framework and statutory authority for congressional financial disclosure data usage',
};

export default function LegalBasisPage() {
  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
          <Scale className="h-8 w-8" />
          Legal Basis for Data Usage
        </h1>
        <p className="text-muted-foreground mt-2">
          Understanding the statutory authority and compliance framework
        </p>
      </div>

      {/* Primary Legal Authority */}
      <Card>
        <CardHeader>
          <CardTitle>5 U.S.C. § 13107 - Financial Disclosure</CardTitle>
          <CardDescription>Ethics in Government Act of 1978 (as amended)</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm">
            The <strong>Ethics in Government Act of 1978</strong> (5 U.S.C. § 13101 et seq.) requires members of Congress
            and other federal officials to disclose their financial interests, transactions, and potential conflicts of interest.
          </p>

          <Alert>
            <FileText className="h-4 w-4" />
            <AlertDescription>
              <strong>5 U.S.C. § 13107(a)</strong> specifically mandates that financial disclosure reports
              "shall be made available to the public" and permits their use for legitimate purposes.
            </AlertDescription>
          </Alert>

          <div className="bg-muted p-4 rounded-md text-sm">
            <p className="font-semibold mb-2">Key Statutory Provisions:</p>
            <ul className="list-disc list-inside space-y-1 ml-2">
              <li>Reports must be filed within 30-45 days of transactions over $1,000</li>
              <li>Reports are public records and available for inspection</li>
              <li>Data may be used for research, transparency, and public interest purposes</li>
              <li>Commercial use restrictions apply (detailed below)</li>
            </ul>
          </div>
        </CardContent>
      </Card>

      {/* Permitted Uses */}
      <Card>
        <CardHeader>
          <CardTitle>Permitted Uses</CardTitle>
          <CardDescription>Activities expressly authorized by statute</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3 text-sm">
            <div className="flex gap-3">
              <span className="text-green-600 font-bold">✓</span>
              <div>
                <p className="font-semibold">Transparency and Accountability</p>
                <p className="text-muted-foreground">
                  Public access to financial disclosure data to monitor potential conflicts of interest
                </p>
              </div>
            </div>

            <div className="flex gap-3">
              <span className="text-green-600 font-bold">✓</span>
              <div>
                <p className="font-semibold">Research and Analysis</p>
                <p className="text-muted-foreground">
                  Academic research, statistical analysis, and data journalism
                </p>
              </div>
            </div>

            <div className="flex gap-3">
              <span className="text-green-600 font-bold">✓</span>
              <div>
                <p className="font-semibold">News and Media</p>
                <p className="text-muted-foreground">
                  Investigative journalism and public interest reporting
                </p>
              </div>
            </div>

            <div className="flex gap-3">
              <span className="text-green-600 font-bold">✓</span>
              <div>
                <p className="font-semibold">Educational Purposes</p>
                <p className="text-muted-foreground">
                  Civic education and government transparency initiatives
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Prohibited Uses */}
      <Card className="border-destructive/50">
        <CardHeader>
          <CardTitle className="text-destructive">Prohibited Uses</CardTitle>
          <CardDescription>Activities expressly restricted by 5 U.S.C. § 13107(c)</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3 text-sm">
            <div className="flex gap-3">
              <span className="text-red-600 font-bold">✗</span>
              <div>
                <p className="font-semibold">Commercial Solicitation</p>
                <p className="text-muted-foreground">
                  Use for commercial solicitation purposes (except news/media organizations)
                </p>
              </div>
            </div>

            <div className="flex gap-3">
              <span className="text-red-600 font-bold">✗</span>
              <div>
                <p className="font-semibold">Credit Rating Determination</p>
                <p className="text-muted-foreground">
                  Use in determining credit ratings or creditworthiness
                </p>
              </div>
            </div>

            <div className="flex gap-3">
              <span className="text-red-600 font-bold">✗</span>
              <div>
                <p className="font-semibold">Fundraising or Solicitation</p>
                <p className="text-muted-foreground">
                  Use for fundraising, marketing campaigns, or commercial solicitation lists
                </p>
              </div>
            </div>
          </div>

          <Alert variant="destructive" className="mt-4">
            <AlertDescription>
              <strong>Violation Notice:</strong> Knowing and willful use of financial disclosure data
              for prohibited purposes may result in civil penalties under 5 U.S.C. § 13107(c).
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>

      {/* Our Compliance */}
      <Card>
        <CardHeader>
          <CardTitle>Our Compliance Commitment</CardTitle>
          <CardDescription>How this platform adheres to legal requirements</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <p>
            This platform is operated solely for <strong>transparency, research, and public interest purposes</strong>.
            We strictly comply with all provisions of 5 U.S.C. § 13107 and related regulations.
          </p>

          <div className="bg-muted p-4 rounded-md space-y-2">
            <p className="font-semibold">Compliance Measures:</p>
            <ul className="list-disc list-inside space-y-1 ml-2">
              <li>Data sourced exclusively from official House Clerk and Senate disclosures</li>
              <li>No commercial solicitation or marketing use</li>
              <li>Open-source codebase for transparency and audit</li>
              <li>Educational and research-focused mission</li>
              <li>Prohibition on data resale or redistribution for commercial purposes</li>
            </ul>
          </div>
        </CardContent>
      </Card>

      {/* Additional Resources */}
      <Card>
        <CardHeader>
          <CardTitle>Additional Legal Resources</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3 text-sm">
            <Link
              href="https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title5-section13107&num=0&edition=prelim"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 text-primary hover:underline"
            >
              <ExternalLink className="h-4 w-4" />
              5 U.S.C. § 13107 (Full Text)
            </Link>

            <Link
              href="https://clerk.house.gov/public-disclosure"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 text-primary hover:underline"
            >
              <ExternalLink className="h-4 w-4" />
              House Clerk Financial Disclosure Portal
            </Link>

            <Link
              href="https://www.ethics.senate.gov/public/index.cfm/financialdisclosure"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 text-primary hover:underline"
            >
              <ExternalLink className="h-4 w-4" />
              Senate Ethics Committee Disclosures
            </Link>
          </div>
        </CardContent>
      </Card>

      {/* Footer Navigation */}
      <div className="flex gap-4 pt-6 border-t">
        <Link href="/legal/terms" className="text-sm text-primary hover:underline">
          Terms of Service →
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
