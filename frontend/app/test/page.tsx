// app/test/page.tsx
import { pingBackend } from "@/lib/api";

export default async function TestPage() {
  const result = await pingBackend();

  return (
    <main className="min-h-screen p-8">
      <h1 className="text-2xl font-bold mb-4">Test Page</h1>
      <p>This is a brand new page.</p>
      <div className="mt-6 p-4 bg-gray-100 dark:bg-gray-800 rounded-lg">
        <h2 className="text-lg font-semibold mb-2">Backend Response:</h2>
        <pre className="text-sm overflow-auto">
          {JSON.stringify(result, null, 2)}
        </pre>
      </div>
    </main>
  );
}
