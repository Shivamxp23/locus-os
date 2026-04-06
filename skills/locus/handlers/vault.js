import { locusStubResponse } from "./stub-util.js";

/** §7.3 vault search — alias of Appledore vault search for architecture parity. */
export default async function vault(params) {
  return locusStubResponse("vault", params);
}
