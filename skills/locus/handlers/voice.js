import { locusStubResponse } from "./stub-util.js";

export default async function voice(params) {
  return locusStubResponse("voice", params);
}
