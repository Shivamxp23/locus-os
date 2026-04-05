// Locus Skill Handler — Voice Note
// POST /api/v1/log/voice

const LOCUS_API = process.env.LOCUS_API_URL || 'http://localhost:3000';
const SERVICE_TOKEN = process.env.LOCUS_SERVICE_TOKEN || '';

export default async function voice(params) {
  const { audioData, mimeType } = params;

  console.log('[locus:voice] called with mimeType:', mimeType);

  try {
    const res = await fetch(`${LOCUS_API}/api/v1/log/voice`, {
      method: 'POST',
      headers: {
        'Content-Type': mimeType || 'audio/ogg',
        'Authorization': `Bearer ${SERVICE_TOKEN}`,
      },
      body: audioData,
    });

    const data = await res.json();
    return data;
  } catch (err) {
    console.error('[locus:voice] error:', err.message);
    return { error: err.message };
  }
}
