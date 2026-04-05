// Locus Skill Handler — Capture (inbox)
// POST /api/v1/log/capture

const LOCUS_API = process.env.LOCUS_API_URL || 'http://localhost:3000';
const SERVICE_TOKEN = process.env.LOCUS_SERVICE_TOKEN || '';

export default async function capture(params) {
  const { content, type } = params;

  console.log('[locus:capture] called with type:', type || 'note');

  try {
    const res = await fetch(`${LOCUS_API}/api/v1/log/capture`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${SERVICE_TOKEN}`,
      },
      body: JSON.stringify({ content, type: type || 'note' }),
    });

    const data = await res.json();
    return data;
  } catch (err) {
    console.error('[locus:capture] error:', err.message);
    return { error: err.message };
  }
}
