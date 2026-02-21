import { Link } from 'react-router-dom'

function DocSection({ title, children }) {
  return (
    <section className="mb-8">
      <h2 className="text-xl font-bold text-dk-5 mb-3 border-b border-dk-3 pb-2">{title}</h2>
      <div className="text-dk-5/90 space-y-2">{children}</div>
    </section>
  )
}

function DocNote({ variant = 'info', title, children }) {
  const styles = {
    info: 'bg-dk-3/50 border-dk-3 text-dk-5',
    warning: 'bg-amber-500/15 border-amber-500/50 text-amber-200',
  }
  return (
    <div className={`rounded-lg border p-4 my-3 ${styles[variant] || styles.info}`}>
      {title && <p className="font-semibold mb-1">{title}</p>}
      <div className="text-sm">{children}</div>
    </div>
  )
}

function DocumentationPage() {
  return (
    <div className="max-w-3xl mx-auto">
      <h1 className="text-3xl font-bold mb-2 text-dk-5">Documentation</h1>
      <p className="text-dk-5/80 mb-6">How to use Brickgen and an overview of features from a UI/UX perspective.</p>
      <p className="text-dk-5/80 mb-8">
        For the HTTP API reference (OpenAPI/Swagger), see <a href="/docs" target="_blank" rel="noopener noreferrer" className="text-mint hover:underline">OpenAPI docs</a>. When the UI is served from a separate dev server, the API docs are at the API origin (e.g. <code className="bg-dk-3 px-1 rounded">http://localhost:8000/docs</code>).
      </p>

      <DocSection title="Getting started">
        <DocNote variant="info" title="Onboarding Wizard">
          When you first open BrickGen, an interactive onboarding wizard will guide you through the initial setup, including downloading the LDraw library and explaining key settings. You can skip it anytime and complete setup manually.
        </DocNote>
        <ol className="list-decimal list-inside space-y-2">
          <li><strong>Search for a set</strong> — Use the search box on the home page. For best results with API limits (see below), find the set on <a href="https://rebrickable.com" target="_blank" rel="noopener noreferrer" className="text-mint hover:underline">Rebrickable</a> and copy the <strong>set number</strong> (e.g. <code className="bg-dk-3 px-1 rounded">21348-1</code>) into Brickgen.</li>
          <li><strong>Open set details</strong> — Click a set in the results to see its details and parts list.</li>
          <li><strong>Create a project</strong> — From the set page, enter a project name and click “Create project”.</li>
          <li><strong>Generate STL</strong> — Open the project from <Link to="/projects" className="text-mint hover:underline">Projects</Link>, configure options if needed, and run the generation job. Download the STL when it’s ready.</li>
        </ol>
      </DocSection>

      <DocNote variant="warning" title="Rebrickable API limits">
        The Rebrickable API allows around <strong>300 requests per month</strong> on the free tier. Each search and many set/part lookups count as requests. To reduce usage, we recommend <strong>searching on Rebrickable first</strong>, then copying the set number (e.g. <code className="bg-dk-3 px-1 rounded">21348-1</code>) into Brickgen’s search. Searching by set number uses fewer API calls and is more reliable.
      </DocNote>

      <DocSection title="Search (home page)">
        <ul className="list-disc list-inside space-y-1">
          <li><strong>Search box</strong> — Type a set name or set number. Submit with the Search button or Enter.</li>
          <li><strong>Suggestions</strong> — As you type, suggestions appear below the field. Click a suggestion to fill the set number and search quickly.</li>
          <li><strong>Recent searches</strong> — Past queries are shown as chips; click to run again or use the × to remove from history.</li>
          <li><strong>Results grid</strong> — Cards show set image, name, set number, year, piece count, and theme. Click a card to open the set detail page.</li>
          <li><strong>Pagination</strong> — Use “Items per page” and Previous/Next to browse large result sets.</li>
        </ul>
      </DocSection>

      <DocSection title="Set detail page">
        <ul className="list-disc list-inside space-y-1">
          <li><strong>Set info</strong> — Image, name, set number, and metadata (year, pieces, theme).</li>
          <li><strong>Parts list</strong> — Paginated list of parts in the set. Part previews can be generated on demand or automatically (see Settings).</li>
          <li><strong>Create project</strong> — Name your project and create it from this set. You can then open it from Projects to generate STL files.</li>
          <li><strong>Back to search</strong> — Returns to the home page and restores your last search results when available.</li>
        </ul>
      </DocSection>

      <DocSection title="Projects">
        <p className="mb-2">Access from the <strong>Projects</strong> link in the header.</p>
        <ul className="list-disc list-inside space-y-1">
          <li><strong>Project list</strong> — All projects with thumbnail, name, and set number. Click a row to open the project.</li>
          <li><strong>Project detail</strong> — View project info, configure generation options (plate size, spacing, STL scale, rotation, LDView options), start a generate job, and download the resulting STL.</li>
          <li><strong>Delete</strong> — Remove a project and its jobs/output from the list (with confirmation).</li>
        </ul>
      </DocSection>

      <DocSection title="Settings">
        <p className="mb-2">Access from the <strong>Settings</strong> link in the header. Five tabs are available; the Cache and Database tabs have dedicated URLs (<code className="bg-dk-3 px-1 rounded">/settings/cache</code>, <code className="bg-dk-3 px-1 rounded">/settings/database</code>).</p>
        <ul className="list-disc list-inside space-y-2">
          <li><strong>General</strong> — Rebrickable API key (write-only; enter a new key to update). Part previews: option to auto-generate part previews, with a link to manage the part-preview cache. System paths (read-only): LDraw library path, cache directory, database path; these are set via environment variables.</li>
          <li><strong>Part</strong> — Build plate size (width, depth, height in mm) and part spacing. Part rotation: enable global rotation and set X/Y/Z degrees; option to match default orientation to preview (studs up). STL scaling factor (0.01–10, default 1.0).</li>
          <li><strong>LDView</strong> — Rendering options used when converting parts to STL and when generating part previews (e.g. quality studs, curve quality, lighting, textures, antialiasing). Each option shows whether it affects STL, Preview, or both. Changing any option clears the STL cache. Basic and advanced sections available; some settings are marked for performance impact.</li>
          <li><strong>Cache</strong> — View and manage caches: STL cache stats; Rebrickable cache (cached sets list, clear); part preview cache (list, clear); LDraw cache (stats, clear or download); search history (list, clear). Clearing Rebrickable or preview cache frees space but may increase API usage when you search or open sets again.</li>
          <li><strong>Database</strong> — Read-only view: database path, applied migrations, current revision, and row counts per table.</li>
        </ul>
      </DocSection>

      <DocSection title="Attributions">
        <p>Third-party software and data sources (LDraw, Rebrickable, LDView, etc.) are listed on the <Link to="/attributions" className="text-mint hover:underline">Attributions</Link> page.</p>
      </DocSection>
    </div>
  )
}

export default DocumentationPage
