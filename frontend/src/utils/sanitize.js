// Strip HTML tags and trim whitespace to prevent XSS in form submissions
export const sanitize = (str) => {
  if (typeof str !== "string") return str;
  return str.replace(/<[^>]*>/g, "").trim();
};

export const sanitizeFormData = (data) => {
  const result = {};
  for (const [key, value] of Object.entries(data)) {
    result[key] = typeof value === "string" ? sanitize(value) : value;
  }
  return result;
};
