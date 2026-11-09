/**
 * Server-side access to the FastAPI backend.
 *
 * Every getter awaits `connection()` first, so pages fetch at request time and `next build` never
 * needs the API to be running. The fetch itself is wrapped in `"use cache"`: the data only changes
 * when the pipeline is rebuilt, so one response serves every visitor for an hour.
 */
import { cacheLife } from "next/cache";
import { connection } from "next/server";
import createClient from "openapi-fetch";

import type { components, paths } from "./schema";

type Schemas = components["schemas"];
export type Meta = Schemas["Meta"];
export type SeasonInfo = Schemas["SeasonInfo"];
export type MvpOverview = Schemas["MvpOverview"];
export type MvpSeasonResult = Schemas["MvpSeasonResult"];
export type EraAccuracy = Schemas["EraAccuracy"];
export type MvpRace = Schemas["MvpRace"];
export type MvpCandidate = Schemas["MvpCandidate"];
export type PlayerRef = Schemas["PlayerRef"];
export type TeamRef = Schemas["TeamRef"];

export const API_URL = process.env.API_URL ?? "http://localhost:8000";

const api = createClient<paths>({ baseUrl: API_URL });

export class ApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiError";
  }
}

type ApiResult<T> = { data?: T; error?: unknown; response: Response };

/** The response body; `null` for a 404; throws for anything else. */
function unwrap<T>({ data, error, response }: ApiResult<T>): T | null {
  if (response.status === 404) return null;
  if (error !== undefined || data === undefined) {
    throw new ApiError(`${response.url} returned ${response.status}`);
  }
  return data;
}

async function call<T>(request: () => Promise<ApiResult<T>>): Promise<T | null> {
  try {
    return unwrap(await request());
  } catch (cause) {
    if (cause instanceof ApiError) throw cause;
    throw new ApiError(`Could not reach the API at ${API_URL}: ${String(cause)}`);
  }
}

function required<T>(value: T | null, what: string): T {
  if (value === null) throw new ApiError(`${what} not found`);
  return value;
}

// --- cached fetches ---------------------------------------------------------------------------------

async function fetchMeta() {
  "use cache";
  cacheLife("hours");
  return call(() => api.GET("/api/v1/meta"));
}

async function fetchMvpOverview() {
  "use cache";
  cacheLife("hours");
  return call(() => api.GET("/api/v1/mvp"));
}

async function fetchMvpRace(season: string) {
  "use cache";
  cacheLife("hours");
  return call(() => api.GET("/api/v1/mvp/{season}", { params: { path: { season }, query: { limit: 50 } } }));
}

// --- public getters ---------------------------------------------------------------------------------

export async function getMeta(): Promise<Meta> {
  await connection();
  return required(await fetchMeta(), "Meta");
}

export async function getMvpOverview(): Promise<MvpOverview> {
  await connection();
  return required(await fetchMvpOverview(), "MVP overview");
}

/** `null` when the season has no MVP data. */
export async function getMvpRace(season: string): Promise<MvpRace | null> {
  await connection();
  return fetchMvpRace(season);
}
