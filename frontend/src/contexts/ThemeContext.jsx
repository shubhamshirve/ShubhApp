import { createContext, useContext, useState, useEffect } from "react";

// E-Bill Theme Definitions
export const themes = {
  modern: {
    name: "Modern",
    description: "Fresh blue theme (Default)",
    primary: "#3B82F6",      // Blue-500
    primaryHover: "#2563EB", // Blue-600
    secondary: "#10B981",    // Emerald-500
    accent: "#6366F1",       // Indigo-500
    sidebar: "#1E293B",      // Slate-800
    sidebarHover: "#334155", // Slate-700
    headerBg: "#FFFFFF",
    pageBg: "#F8FAFC",       // Slate-50
    cardBg: "#FFFFFF",
    textPrimary: "#0F172A",  // Slate-900
    textSecondary: "#64748B", // Slate-500
    border: "#E2E8F0",       // Slate-200
  },
  classic: {
    name: "Classic",
    description: "E-Bill brand colors",
    primary: "#0066B2",      // EB Blue
    primaryHover: "#004080", // EB Deep Blue
    secondary: "#44AB62",    // EB Green
    accent: "#004080",       // EB Deep Blue
    sidebar: "#004080",      // EB Deep Blue
    sidebarHover: "#0066B2", // EB Blue
    headerBg: "#FFFFFF",
    pageBg: "#EFEFEF",       // Cool Gray
    cardBg: "#FFFFFF",
    textPrimary: "#004080",  // EB Deep Blue
    textSecondary: "#64748B",
    border: "#CBD5E1",
  }
};

const ThemeContext = createContext({
  theme: "modern",
  themeConfig: themes.modern,
  setTheme: () => {},
  loading: true,
});

export const useTheme = () => useContext(ThemeContext);

export const ThemeProvider = ({ children, authAxios, user }) => {
  const [theme, setThemeState] = useState("modern");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTheme = async () => {
      if (!user || user.role === "admin") {
        // Admin uses modern theme by default
        setThemeState("modern");
        setLoading(false);
        return;
      }
      
      try {
        const res = await authAxios.get("/operator/theme-settings");
        setThemeState(res.data.theme || "modern");
      } catch (err) {
        // Default to modern for new users
        setThemeState("modern");
      } finally {
        setLoading(false);
      }
    };

    if (authAxios && user) {
      fetchTheme();
    } else {
      setLoading(false);
    }
  }, [authAxios, user]);

  const setTheme = async (newTheme) => {
    if (newTheme === theme) return;
    
    try {
      if (authAxios && user && user.role !== "admin") {
        await authAxios.put(`/operator/theme-settings?theme=${newTheme}`);
      }
      setThemeState(newTheme);
    } catch (err) {
      console.error("Failed to save theme:", err);
    }
  };

  const themeConfig = themes[theme] || themes.modern;

  return (
    <ThemeContext.Provider value={{ theme, themeConfig, setTheme, loading }}>
      {children}
    </ThemeContext.Provider>
  );
};

export default ThemeContext;
