export interface ApiErrorBody {
  detail?: string;
  [field: string]: unknown;
}

/**
 * DRF errors come back in two shapes: {detail: "..."} for view-level rejections
 * (permission/auth/not-found), or {field: ["msg", ...]} for serializer validation errors
 * (e.g. {status: ["Complete Stripe onboarding before publishing products."]}). Without this,
 * every field-validation error in the app would silently fall back to a generic
 * "Request failed with status 400" instead of the actual, useful message.
 */
function extractMessage(status: number, body: ApiErrorBody): string {
  if (typeof body.detail === "string") return body.detail;

  for (const value of Object.values(body)) {
    if (Array.isArray(value) && typeof value[0] === "string") return value[0];
    if (typeof value === "string") return value;
  }

  return `Request failed with status ${status}`;
}

export class ApiError extends Error {
  status: number;
  body: ApiErrorBody;

  constructor(status: number, body: ApiErrorBody) {
    super(extractMessage(status, body));
    this.status = status;
    this.body = body;
  }
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
