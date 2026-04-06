import { locusStubResponse } from "./stub-util.js";

export default async function morningLog(params) {
  return locusStubResponse("morning_log", params);
}
