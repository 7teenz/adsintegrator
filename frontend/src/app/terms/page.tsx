export default function TermsPage() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <h1 className="text-3xl font-semibold text-slate-900">Terms of Service</h1>
      <p className="mt-3 text-sm text-slate-500">Last updated: March 20, 2026</p>

      <div className="mt-8 space-y-8 text-sm leading-6 text-slate-700">
        <section>
          <h2 className="text-lg font-semibold text-slate-900">Service scope</h2>
          <p className="mt-2">Meta Ads Audit provides analytics, audit scoring, and recommendations based on advertising data you upload or sync. The service is informational and does not guarantee campaign outcomes.</p>
        </section>
        <section>
          <h2 className="text-lg font-semibold text-slate-900">Account responsibility</h2>
          <p className="mt-2">You are responsible for the accuracy of uploaded data, maintaining the security of your account, and ensuring you have authority to connect or upload advertising account information.</p>
        </section>
        <section>
          <h2 className="text-lg font-semibold text-slate-900">Acceptable use</h2>
          <p className="mt-2">You may not misuse the service, attempt unauthorized access, interfere with platform operation, or upload unlawful data.</p>
        </section>
        <section>
          <h2 className="text-lg font-semibold text-slate-900">Data and deletion</h2>
          <p className="mt-2">You retain responsibility for your uploaded and connected advertising data. You may request deletion of your account and associated stored data by contacting support.</p>
        </section>
        <section>
          <h2 className="text-lg font-semibold text-slate-900">Availability</h2>
          <p className="mt-2">The service may change, be interrupted, or be withdrawn at any time, especially during beta or limited-release operation.</p>
        </section>
        <section>
          <h2 className="text-lg font-semibold text-slate-900">Contact</h2>
          <p className="mt-2">For support or legal questions, contact <a className="text-brand-600" href="mailto:contact@yourdomain.com">contact@yourdomain.com</a>.</p>
        </section>
      </div>
    </main>
  );
}
