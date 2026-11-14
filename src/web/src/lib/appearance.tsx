import {
  createContext,
  useContext,
  useEffect,
  useLayoutEffect,
  useState,
  type ReactNode,
} from "react";
import { Theme } from "@astryxdesign/core/theme";
import { neutralTheme } from "@astryxdesign/theme-neutral/built";

export type Appearance = "light" | "dark" | "system";
export type ColorMode = "light" | "dark";
export const APPEARANCE_KEY = "trendscope.appearance";
const AppearanceContext = createContext<{
  appearance: Appearance;
  resolved: ColorMode;
  setAppearance: (mode: Appearance) => void;
}>({ appearance: "system", resolved: "light", setAppearance: () => {} });

function storedAppearance(): Appearance {
  try {
    const value = localStorage.getItem(APPEARANCE_KEY);
    if (value === "light" || value === "dark") return value;
  } catch {
    /* System mode is usable without storage. */
  }
  return "system";
}

export function AppearanceProvider({ children }: { children: ReactNode }) {
  const [appearance, setMode] = useState<Appearance>(storedAppearance);
  const [systemDark, setSystemDark] = useState(
    () => window.matchMedia("(prefers-color-scheme: dark)").matches,
  );
  const resolved =
    appearance === "system" ? (systemDark ? "dark" : "light") : appearance;
  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const change = () => setSystemDark(media.matches);
    media.addEventListener("change", change);
    change();
    return () => media.removeEventListener("change", change);
  }, []);
  useLayoutEffect(() => {
    document.documentElement.dataset.mode = resolved;
    document.documentElement.style.colorScheme = resolved;
  }, [resolved]);
  const setAppearance = (mode: Appearance) => {
    setMode(mode);
    try {
      localStorage.setItem(APPEARANCE_KEY, mode);
    } catch {
      /* Keep the in-memory choice. */
    }
  };
  return (
    <Theme theme={neutralTheme} mode={resolved}>
      <AppearanceContext.Provider
        value={{ appearance, resolved, setAppearance }}
      >
        {children}
      </AppearanceContext.Provider>
    </Theme>
  );
}
export const useAppearance = () => useContext(AppearanceContext);
