import { locusStubResponse } from "./stub-util.js";

export default async function query(params) {
  return locusStubResponse("query", params);
}
