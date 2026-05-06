import { AlertCircle, Database, Factory, LogIn, LogOut, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  getBuildingRegistry,
  getCurrentDenizen,
  getCurrentRules,
  getUpkeepPreview,
  login,
} from "./api";
import type {
  AuthDenizen,
  BuildingRegistrySummary,
  BuildingUpkeepSummary,
  RulesDataset,
} from "./types";

type LoadState = {
  rules?: RulesDataset;
  buildings?: BuildingRegistrySummary;
  upkeep?: BuildingUpkeepSummary;
  error?: string;
  isLoading: boolean;
};

const numberFormatter = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 2,
});

const TOKEN_STORAGE_KEY = "carta-auth-token";

export function App() {
  const [state, setState] = useState<LoadState>({ isLoading: true });
  const [authToken, setAuthToken] = useState(() => localStorage.getItem(TOKEN_STORAGE_KEY));
  const [currentDenizen, setCurrentDenizen] = useState<AuthDenizen | undefined>();
  const [authError, setAuthError] = useState<string | undefined>();
  const [isAuthLoading, setIsAuthLoading] = useState(false);

  const loadDashboard = useCallback(async () => {
    setState((current) => ({ ...current, error: undefined, isLoading: true }));
    try {
      const [rules, buildings, upkeep] = await Promise.all([
        getCurrentRules(),
        getBuildingRegistry(),
        getUpkeepPreview(),
      ]);
      setState({ rules, buildings, upkeep, isLoading: false });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to load dashboard data";
      setState((current) => ({ ...current, error: message, isLoading: false }));
    }
  }, []);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  useEffect(() => {
    if (!authToken) {
      setCurrentDenizen(undefined);
      return;
    }

    let isMounted = true;
    setIsAuthLoading(true);
    getCurrentDenizen(authToken)
      .then((denizen) => {
        if (!isMounted) {
          return;
        }
        setCurrentDenizen(denizen);
        setAuthError(undefined);
      })
      .catch(() => {
        if (!isMounted) {
          return;
        }
        localStorage.removeItem(TOKEN_STORAGE_KEY);
        setAuthToken(null);
        setCurrentDenizen(undefined);
        setAuthError("Session expired. Sign in again.");
      })
      .finally(() => {
        if (isMounted) {
          setIsAuthLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [authToken]);

  const handleLogin = async (email: string, password: string) => {
    setIsAuthLoading(true);
    setAuthError(undefined);
    try {
      const session = await login(email, password);
      localStorage.setItem(TOKEN_STORAGE_KEY, session.access_token);
      setAuthToken(session.access_token);
      setCurrentDenizen(session.denizen);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to sign in";
      setAuthError(message);
    } finally {
      setIsAuthLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    setAuthToken(null);
    setCurrentDenizen(undefined);
    setAuthError(undefined);
  };

  const buildingNames = useMemo(() => {
    return new Map(
      state.rules?.building_definitions.map((building) => [building.key, building.name]) ?? [],
    );
  }, [state.rules]);

  const upkeepTotal = state.upkeep?.totals.reduce((total, item) => total + item.amount, 0) ?? 0;

  return (
    <main className="app-shell">
      <header className="top-bar">
        <div>
          <p className="eyebrow">Carta Arcanum</p>
          <h1>Settlement planning dashboard</h1>
        </div>
        <div className="top-actions">
          <SessionPanel
            authError={authError}
            currentDenizen={currentDenizen}
            isLoading={isAuthLoading}
            onLogin={handleLogin}
            onLogout={handleLogout}
          />
          <button
            aria-label="Refresh dashboard data"
            className="icon-button"
            disabled={state.isLoading}
            onClick={() => void loadDashboard()}
            title="Refresh dashboard data"
            type="button"
          >
            <RefreshCw aria-hidden="true" size={20} />
          </button>
        </div>
      </header>

      {state.error ? (
        <section className="status-banner" role="alert">
          <AlertCircle aria-hidden="true" size={20} />
          <span>{state.error}</span>
        </section>
      ) : null}

      <section className="metric-grid" aria-label="Rules summary">
        <Metric label="Rules version" value={state.rules?.rules_version ?? "..."} />
        <Metric label="Buildings" value={state.rules?.building_definitions.length ?? "..."} />
        <Metric label="Recipes" value={state.rules?.production_recipes.length ?? "..."} />
        <Metric label="Visible records" value={state.buildings?.items.length ?? "..."} />
      </section>

      <section className="content-grid">
        <div className="panel panel-wide">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Registry</p>
              <h2>Visible buildings</h2>
            </div>
            <Database aria-hidden="true" size={20} />
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Denizen</th>
                  <th>House</th>
                  <th>Count</th>
                </tr>
              </thead>
              <tbody>
                {(state.buildings?.items ?? []).map((building) => (
                  <tr key={building.id}>
                    <td>
                      {building.display_name ??
                        buildingNames.get(building.building_definition_id) ??
                        building.building_definition_id}
                    </td>
                    <td>{building.owner_denizen_id}</td>
                    <td>{building.house_id ?? "Personal"}</td>
                    <td>{building.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {state.buildings?.note ? <p className="muted">{state.buildings.note}</p> : null}
        </div>

        <div className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Upkeep</p>
              <h2>Current totals</h2>
            </div>
            <Factory aria-hidden="true" size={20} />
          </div>
          <div className="total-line">
            <span>Tracked requirement</span>
            <strong>{numberFormatter.format(upkeepTotal)}</strong>
          </div>
          <ul className="resource-list">
            {(state.upkeep?.totals ?? []).map((item) => (
              <li key={`${item.item_type}:${item.item_key}`}>
                <span>{item.item_key}</span>
                <strong>{numberFormatter.format(item.amount)}</strong>
              </li>
            ))}
          </ul>
        </div>

        <div className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Rules</p>
              <h2>Dataset shape</h2>
            </div>
          </div>
          <ul className="resource-list">
            <li>
              <span>Currencies</span>
              <strong>{state.rules?.currencies.length ?? "..."}</strong>
            </li>
            <li>
              <span>Resources</span>
              <strong>{state.rules?.resources.length ?? "..."}</strong>
            </li>
            <li>
              <span>Units</span>
              <strong>{state.rules?.units.length ?? "..."}</strong>
            </li>
            <li>
              <span>Transports</span>
              <strong>{state.rules?.transports.length ?? "..."}</strong>
            </li>
          </ul>
        </div>
      </section>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function SessionPanel({
  authError,
  currentDenizen,
  isLoading,
  onLogin,
  onLogout,
}: {
  authError?: string;
  currentDenizen?: AuthDenizen;
  isLoading: boolean;
  onLogin: (email: string, password: string) => Promise<void>;
  onLogout: () => void;
}) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  if (currentDenizen) {
    return (
      <section className="session-panel" aria-label="Current session">
        <div>
          <span>Signed in</span>
          <strong>{currentDenizen.display_name}</strong>
        </div>
        <button className="text-button" onClick={onLogout} type="button">
          <LogOut aria-hidden="true" size={16} />
          Sign out
        </button>
      </section>
    );
  }

  return (
    <form
      className="login-form"
      onSubmit={(event) => {
        event.preventDefault();
        void onLogin(email, password);
      }}
    >
      <label>
        <span>Email</span>
        <input
          autoComplete="email"
          onChange={(event) => setEmail(event.target.value)}
          required
          type="email"
          value={email}
        />
      </label>
      <label>
        <span>Password</span>
        <input
          autoComplete="current-password"
          onChange={(event) => setPassword(event.target.value)}
          required
          type="password"
          value={password}
        />
      </label>
      <button className="text-button" disabled={isLoading} type="submit">
        <LogIn aria-hidden="true" size={16} />
        Sign in
      </button>
      {authError ? <p role="alert">{authError}</p> : null}
    </form>
  );
}
