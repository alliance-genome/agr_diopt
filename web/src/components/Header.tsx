import { Moon, Sun } from "lucide-react";

export function Header({ theme, onToggleTheme }: { theme: string; onToggleTheme: () => void }) {
  const next = theme === "dark" ? "light" : "dark";
  return (
    <header className="site-header">
      <div className="logo-row">
        <a className="alliance-logo" href="https://www.alliancegenome.org">
          <img
            src={theme === "dark" ? "/alliance_logo_white.png" : "/alliance_logo_agr.png"}
            alt="Alliance of Genome Resources"
            width={200}
            height={48}
          />
        </a>
        <a className="app-name" href="/">
          DIOPT
        </a>
        <button
          type="button"
          className="secondary theme-toggle"
          onClick={onToggleTheme}
          aria-label={`Switch to ${next} mode`}
        >
          {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
          {theme === "dark" ? "Light mode" : "Dark mode"}
        </button>
      </div>
      <nav className="brand-band" aria-label="Breadcrumb">
        <ol>
          <li>
            <a href="https://www.alliancegenome.org">Alliance home</a>
          </li>
          <li aria-current="page">DIOPT</li>
        </ol>
      </nav>
    </header>
  );
}
