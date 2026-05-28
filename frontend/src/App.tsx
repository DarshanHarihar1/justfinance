export default function App() {
  const apiUrl = import.meta.env.VITE_API_URL ?? "(VITE_API_URL not set)";

  return (
    <main className="min-h-screen bg-neutral-50 text-neutral-900">
      <div className="mx-auto flex max-w-xl flex-col gap-6 px-6 py-24">
        <h1 className="text-3xl font-semibold tracking-tight">
          Finance Tracker
        </h1>
        <p className="text-neutral-600">
          Phase&nbsp;1 infrastructure online. The real UI lands in Phase&nbsp;6.
        </p>
        <dl className="rounded-md border border-neutral-200 bg-white p-4 text-sm">
          <div className="flex items-center justify-between gap-4">
            <dt className="text-neutral-500">Backend API</dt>
            <dd className="font-mono">{apiUrl}</dd>
          </div>
        </dl>
      </div>
    </main>
  );
}
