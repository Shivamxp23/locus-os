// Locus Skill Handler — Appledore Search (Obsidian vault)
// POST /api/v1/appledore/search

const LOCUS_API = process.env.LOCUS_API_URL || 'http://localhost:3000';
const SERVICE_TOKEN = process.env.LOCUS_SERVICE_TOKEN || '';

export default async function appledore(params) {
  const { query } = params;

  console.log('[locus:appledore] called with query:', query);

  try {
    const res = await fetch(`${LOCUS_API}/api/v1/appledore/search`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${SERVICE_TOKEN}`,
      },
      body: JSON.stringify({ query }),
    });

    const data = await res.json();
    return data;
  } catch (err) {
    console.error('[locus:appledore] error:', err.message);
    return { error: err.message };
  }
}
