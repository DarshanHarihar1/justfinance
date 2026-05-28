import { useTheme, type Theme } from "@/lib/theme";

const options: { value: Theme; label: string }[] = [
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
  { value: "system", label: "System" },
];

export function AppearanceSection() {
  const { theme, setTheme } = useTheme();

  return (
    <section className="mt-12">
      <h2 className="mb-4 text-sm font-medium text-[--color-text-muted]">Appearance</h2>
      <fieldset className="flex flex-wrap gap-6">
        <legend className="sr-only">Theme</legend>
        {options.map((opt) => (
          <label key={opt.value} className="flex cursor-pointer items-center gap-2 text-sm">
            <input
              type="radio"
              name="theme"
              value={opt.value}
              checked={theme === opt.value}
              onChange={() => setTheme(opt.value)}
              className="border-[--color-border-strong] text-[--color-accent] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[--color-accent]"
            />
            {opt.label}
          </label>
        ))}
      </fieldset>
    </section>
  );
}
