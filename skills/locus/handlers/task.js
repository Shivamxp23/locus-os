// Locus Skill Handler — Task Management
// POST /api/v1/tasks/{action}

const LOCUS_API = process.env.LOCUS_API_URL || 'http://localhost:3000';
const SERVICE_TOKEN = process.env.LOCUS_SERVICE_TOKEN || '';

export default async function task(params) {
  const { action, ...body } = params;

  console.log(`[locus:task] called with action=${action}`, body);

  try {
    const res = await fetch(`${LOCUS_API}/api/v1/tasks/${action}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${SERVICE_TOKEN}`,
      },
      body: JSON.stringify(body),
    });

    const data = await res.json();
    return data;
  } catch (err) {
    console.error('[locus:task] error:', err.message);
    return { error: err.message };
  }
}
