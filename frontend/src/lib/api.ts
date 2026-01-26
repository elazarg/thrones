/**
 * Parse an error response from the API.
 *
 * FastAPI returns JSON with a "detail" field for HTTPException errors.
 * This function handles both JSON and plain text error responses.
 */
export async function parseErrorResponse(response: Response): Promise<string> {
  const contentType = response.headers.get('content-type') || '';

  if (contentType.includes('application/json')) {
    try {
      const json = await response.json();
      // FastAPI HTTPException format
      if (json.detail) {
        return typeof json.detail === 'string'
          ? json.detail
          : JSON.stringify(json.detail);
      }
      // Generic JSON error
      if (json.message) {
        return json.message;
      }
      if (json.error) {
        return json.error;
      }
      return JSON.stringify(json);
    } catch {
      // JSON parse failed, fall through to text
    }
  }

  // Fallback to plain text
  try {
    const text = await response.text();
    return text || `HTTP ${response.status}: ${response.statusText}`;
  } catch {
    return `HTTP ${response.status}: ${response.statusText}`;
  }
}
