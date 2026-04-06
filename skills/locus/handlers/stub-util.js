/** Phase 1 stub — replace with FastAPI calls in Phase 3 (LOCUS_ARCHITECTURE_v4 §25). */
export function locusStubResponse(handlerName, params) {
  console.log(`[locus:${handlerName}] stub called`, params ?? {});
  return {
    ok: true,
    stub: true,
    handler: handlerName,
    message: "Phase 1 stub — wire to LOCUS_API_URL in Phase 3",
  };
}
