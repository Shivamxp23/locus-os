// Locus Skill Handler — Morning Log
// POST /api/v1/log/morning → { energy, mood, sleep, stress, time_available }

const LOCUS_API = process.env.LOCUS_API_URL || 'http://localhost:3000';
const SERVICE_TOKEN = process.env.LOCUS_SERVICE_TOKEN || '';

export default async function morningLog(params) {
  const { energy, mood, sleep, stress, time_available } = params;

  console.log('[locus:morning_log] called with:', { energy, mood, sleep, stress, time_available });

  try {
    const res = await fetch(`${LOCUS_API}/api/v1/log/morning`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${SERVICE_TOKEN}`,
      },
      body: JSON.stringify({ energy, mood, sleep, stress, time_available }),
    });

    const data = await res.json();
    return data;
  } catch (err) {
    console.error('[locus:morning_log] error:', err.message);
    return { error: err.message };
  }
}
