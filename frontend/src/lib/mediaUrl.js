const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

export function resolveMediaUrl(path) {
  if (!path) {
    return "";
  }

  if (path.startsWith("http://") || path.startsWith("https://") || path.startsWith("data:")) {
    return path;
  }

  if ((path.startsWith("/uploads/") || path.startsWith("/api/uploads/")) && BACKEND_URL) {
    return `${BACKEND_URL}${path}`;
  }

  return path;
}
