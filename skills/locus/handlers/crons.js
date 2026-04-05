// Locus Skill Handler — Crons (scheduled jobs)
// POST /api/v1/internal/jobs/trigger

const LOCUS_API = process.env.LOCUS_API_URL || 'http://localhost:3000';
const SERVICE_TOKEN = process.env.LOCUS_SERVICE_TOKEN || '';

export default async function crons(params) {
  const { job } = params;

  console.log('[locus:crons] triggered job:', job);

  try {
    const res = await fetch(`${LOCUS_API}/api/v1/internal/jobs/trigger`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${SERVICE_TOKEN}`,
      },
      body: JSON.stringify({ job }),
    });

    const data = await res.json();
    return data;
  } catch (err) {
    console.error('[locus:crons] error:', err.message);
    return { error: err.message };
  }
}
