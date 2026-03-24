const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

export function resolveMediaUrl(path) {
  if (!path) {
    return "";
  }

  // If it's already a full URL (http/https) or data URL, return as-is
  if (path.startsWith("http://") || path.startsWith("https://") || path.startsWith("data:")) {
    return path;
  }

  // For relative paths (starting with /)
  if (path.startsWith("/")) {
    // If BACKEND_URL is set, prepend it for API paths
    if (BACKEND_URL && (path.startsWith("/uploads/") || path.startsWith("/api/uploads/"))) {
      return `${BACKEND_URL}${path}`;
    }
    // Otherwise return the path as-is (will be relative to current domain)
    return path;
  }

  // For non-prefixed paths, return as-is
  return path;
}
