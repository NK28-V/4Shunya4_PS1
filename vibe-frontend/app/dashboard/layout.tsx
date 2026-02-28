export default function DashboardLayout({
    children,
  }: {
    children: React.ReactNode;
  }) {
    return (
      <div className="flex min-h-screen">
  
        {/* Sidebar */}
        <aside className="hidden sm:flex flex-col w-60 bg-zinc-950 border-r border-zinc-900 text-zinc-100">
          <div className="px-6 py-6 text-xl font-bold tracking-wide border-b border-zinc-900">
            vibe2value
          </div>
  
          <nav className="flex-1 py-6">
            <ul className="space-y-2">
              <li>
                <a href="/dashboard" className="block px-6 py-2 rounded hover:bg-zinc-900 transition-colors">
                  Overview
                </a>
              </li>
              <li>
                <a href="/dashboard/vulnerabilities" className="block px-6 py-2 rounded hover:bg-zinc-900 transition-colors">
                  Vulnerabilities
                </a>
              </li>
              <li>
                <a href="/dashboard/compliance" className="block px-6 py-2 rounded hover:bg-zinc-900 transition-colors">
                  Compliance
                </a>
              </li>
            </ul>
          </nav>
        </aside>
  
        {/* Main Content */}
        <main className="flex-1 p-8">
          <div className="max-w-6xl mx-auto">
            {children}
          </div>
        </main>
  
      </div>
    );
  }