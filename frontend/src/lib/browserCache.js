export async function clearBrowserCache() {
  if (typeof window === "undefined") {
    return;
  }

  try {
    if ("caches" in window) {
      const keys = await window.caches.keys();
      await Promise.all(
        keys
          .filter((key) => key.startsWith("ebill-"))
          .map((key) => window.caches.delete(key))
      );
    }

    if ("serviceWorker" in navigator) {
      const registrations = await navigator.serviceWorker.getRegistrations();
      await Promise.all(
        registrations.map((registration) =>
          registration.active?.postMessage({ type: "CLEAR_EBILL_CACHE" })
        )
      );
      await Promise.all(
        registrations.map((registration) => registration.update().catch(() => undefined))
      );
    }

    window.sessionStorage.clear();
  } catch (error) {
    console.warn("Failed to clear browser cache", error);
  }
}
