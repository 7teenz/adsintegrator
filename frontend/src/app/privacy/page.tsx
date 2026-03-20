export default function PrivacyPage() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <h1 className="text-3xl font-semibold text-slate-900">Privacy Policy</h1>
      <p className="mt-3 text-sm text-slate-500">Last updated: March 20, 2026</p>

      <div className="mt-8 space-y-8 text-sm leading-6 text-slate-700">
        <section>
          <h2 className="text-lg font-semibold text-slate-900">What we collect</h2>
          <p className="mt-2">We collect your account email, profile details, and advertising performance data that you upload or sync from Meta Ads Manager.</p>
        </section>
        <section>
          <h2 className="text-lg font-semibold text-slate-900">How we use data</h2>
          <p className="mt-2">We use this data only to generate audit reports, health scoring, recommendations, and account analytics inside the product.</p>
        </section>
        <section>
          <h2 className="text-lg font-semibold text-slate-900">Storage and security</h2>
          <p className="mt-2">Uploaded ad data is stored in the application database. Meta OAuth tokens are encrypted at rest. Access is restricted to the authenticated account owner and required application services.</p>
        </section>
        <section>
          <h2 className="text-lg font-semibold text-slate-900">Retention</h2>
          <p className="mt-2">We retain audit data until you delete it or request account deletion. Operational logs may be retained for a limited period for reliability and security monitoring.</p>
        </section>
        <section>
          <h2 className="text-lg font-semibold text-slate-900">Deletion requests</h2>
          <p className="mt-2">You can request deletion of your account and associated data by contacting support. Imported data may also be removed through account settings where available.</p>
        </section>
        <section>
          <h2 className="text-lg font-semibold text-slate-900">Sharing</h2>
          <p className="mt-2">We do not sell your data and we do not share it with third parties except for essential infrastructure and processing needed to operate the service.</p>
        </section>
        <section>
          <h2 className="text-lg font-semibold text-slate-900">Contact</h2>
          <p className="mt-2">For privacy questions or deletion requests, contact <a className="text-brand-600" href="mailto:contact@yourdomain.com">contact@yourdomain.com</a>.</p>
        </section>
      </div>
    </main>
  );
}
