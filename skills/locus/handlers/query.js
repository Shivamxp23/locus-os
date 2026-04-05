// Locus Skill Handler — Query (schedule/today)
// GET /api/v1/schedule/today

const LOCUS_API = process.env.LOCUS_API_URL || 'http://localhost:3000';
const SERVICE_TOKEN = process.env.LOCUS_SERVICE_TOKEN || '';

export default async function query(params) {
  console.log('[locus:query] called with:', params);

  try {
    const res = await fetch(`${LOCUS_API}/api/v1/schedule/today`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${SERVICE_TOKEN}`,
      },
    });

    const data = await res.json();
    return data;
  } catch (err) {
    console.error('[locus:query] error:', err.message);
    return { error: err.message };
  }
}
