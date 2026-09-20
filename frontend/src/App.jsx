import { useEffect, useMemo, useState } from "react";
import "./App.css";
import "./login.css";
import ButterflyMap from "./ButterflyMap";
import {
  firebaseAuth,
  firebaseConfigured,
  googleProvider,
  onAuthStateChanged,
  signInWithPopup,
  signOut,
  getFirebaseIdToken,
} from "./firebase";

const API_URL =
  import.meta.env.VITE_API_URL ||
  "https://atlas-backend-6u1o.onrender.com";

/* =========================================================
   AUTHENTICATED API HELPER
   ========================================================= */

async function apiFetch(url, options = {}) {
  if (!firebaseAuth) {
    throw new Error(
      "Firebase authentication is not configured."
    );
  }

  async function request() {
    const token = await getFirebaseIdToken();
    const headers = new Headers(options.headers || {});

    headers.set(
      "Authorization",
      `Bearer ${token}`
    );

    return fetch(url, {
      ...options,
      headers,
    });
  }

  const response = await request();

  if (response.status !== 401) {
    return response;
  }

  await new Promise((resolve) =>
    window.setTimeout(resolve, 300)
  );

  return request();
}

/* =========================================================
   ICONS
   ========================================================= */

function Icon({ type, size = 20 }) {
  const common = {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round",
    strokeLinejoin: "round",
  };

  const icons = {
    home: (
      <>
        <path d="M3 10.5 12 3l9 7.5" />
        <path d="M5.5 9.5V21h13V9.5" />
        <path d="M9.5 21v-6h5v6" />
      </>
    ),

    scenario: (
      <>
        <circle cx="5" cy="12" r="2" />
        <circle cx="19" cy="6" r="2" />
        <circle cx="19" cy="18" r="2" />
        <path d="m7 11 10-4" />
        <path d="m7 13 10 4" />
      </>
    ),

    graph: (
      <>
        <circle cx="5" cy="12" r="2.5" />
        <circle cx="19" cy="5" r="2.5" />
        <circle cx="19" cy="19" r="2.5" />
        <path d="M7.3 10.7 16.7 6.3" />
        <path d="M7.3 13.3 16.7 17.7" />
      </>
    ),

    timeline: (
      <>
        <circle cx="6" cy="12" r="2" />
        <circle cx="12" cy="7" r="2" />
        <circle cx="18" cy="15" r="2" />
        <path d="M7.7 10.6 10.3 8.4" />
        <path d="m13.7 8.2 2.6 5.6" />
      </>
    ),

    report: (
      <>
        <path d="M6 3h9l3 3v15H6z" />
        <path d="M14 3v4h4" />
        <path d="M9 12h6" />
        <path d="M9 16h6" />
      </>
    ),

    settings: (
      <>
        <circle cx="12" cy="12" r="3" />
        <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-1.7 1.7-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.5v.2h-2.4v-.2a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.9.3l-.1.1L8 17l.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.5-1H6.7v-2.4h.2a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.9L8 8.6l1.7-1.7.1.1a1.7 1.7 0 0 0 1.9.3 1.7 1.7 0 0 0 1-1.5v-.2h2.4v.2a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.9-.3l.1-.1 1.7 1.7-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 .3 1.9 1.7 1.7 0 0 0 1.5 1h.2V14h-.2a1.7 1.7 0 0 0-1.5 1z" />
      </>
    ),

    leaf: (
      <>
        <path d="M20 4C11 4 5 8 5 14c0 3 2 5 5 5 6 0 10-6 10-15Z" />
        <path d="M4 21c3-6 7-9 13-12" />
      </>
    ),

    wheat: (
      <>
        <path d="M12 21V5" />
        <path d="M12 9c-3-1-5-3-5-5 3 0 5 1 5 5Z" />
        <path d="M12 13c-3-1-5-3-5-5 3 0 5 1 5 5Z" />
        <path d="M12 17c-3-1-5-3-5-5 3 0 5 1 5 5Z" />
        <path d="M12 9c3-1 5-3 5-5-3 0-5 1-5 5Z" />
        <path d="M12 13c3-1 5-3 5-5-3 0-5 1-5 5Z" />
        <path d="M12 17c3-1 5-3 5-5-3 0-5 1-5 5Z" />
      </>
    ),

    calendar: (
      <>
        <rect x="4" y="5" width="16" height="15" rx="2" />
        <path d="M8 3v4M16 3v4M4 10h16" />
      </>
    ),

    network: (
      <>
        <circle cx="12" cy="5" r="2.5" />
        <circle cx="5" cy="18" r="2.5" />
        <circle cx="19" cy="18" r="2.5" />
        <path d="m10.8 7.3-4.4 8.4M13.2 7.3l4.4 8.4M7.5 18h9" />
      </>
    ),

    chart: (
      <>
        <path d="M4 19V5" />
        <path d="M4 19h17" />
        <path d="m7 15 4-4 3 2 6-7" />
        <path d="M17 6h3v3" />
      </>
    ),

    shield: (
      <>
        <path d="M12 3 20 6v6c0 5-3.4 8-8 9-4.6-1-8-4-8-9V6l8-3Z" />
        <path d="m9 12 2 2 4-5" />
      </>
    ),

    chat: (
      <>
        <path d="M5 5h14v10H9l-4 4V5Z" />
        <path d="M8 9h8M8 12h5" />
      </>
    ),
  };

  return <svg {...common}>{icons[type] || icons.leaf}</svg>;
}

/* =========================================================
   HELPERS
   ========================================================= */

function formatNumber(value, digits = 1) {
  if (
    value === null ||
    value === undefined ||
    Number.isNaN(Number(value))
  ) {
    return "—";
  }

  return Number(value).toFixed(digits);
}

const shockRegionOptions = [
  { value: "europe", label: "Europe" },
  { value: "france", label: "France" },
  { value: "germany", label: "Germany" },
  { value: "poland", label: "Poland" },
  { value: "romania", label: "Romania" },
  { value: "spain", label: "Spain" },
  { value: "russia", label: "Russia" },
  { value: "canada", label: "Canada" },
  { value: "egypt", label: "Egypt" },
  { value: "morocco", label: "Morocco" },
  { value: "algeria", label: "Algeria" },
];

function getUserInitials(name, email) {
  const source = (name || email || "ATLAS user").trim();
  const words = source.split(/\s+/).filter(Boolean);

  if (words.length > 1) {
    return `${words[0][0]}${words[words.length - 1][0]}`.toUpperCase();
  }

  return source.slice(0, 2).toUpperCase();
}

/* =========================================================
   APP
   ========================================================= */

function App() {
  const [auth, setAuth] = useState(null);

  const [assistantQuestion, setAssistantQuestion] =
    useState("");

  const [assistantMessages, setAssistantMessages] =
    useState([
      {
        role: "assistant",
        text: "Hi. Ask me about food supply, countries, trade, or what this simulation means.",
      },
    ]);

  const [assistantLoading, setAssistantLoading] =
    useState(false);

  const [assistantOpen, setAssistantOpen] =
    useState(false);

  const [activeDashboard, setActiveDashboard] =
    useState("home");

  const [shockRegion, setShockRegion] =
    useState("europe");

  const [shockPercent, setShockPercent] =
    useState(-20);

  const [horizon, setHorizon] =
    useState(6);

  const [alternateSupply, setAlternateSupply] =
    useState(10);

  const [data, setData] = useState(null);
  const [explanation, setExplanation] =
    useState(null);

  const [graphData, setGraphData] =
    useState(null);

  const [dependencyData, setDependencyData] =
    useState(null);

  const [coverageData, setCoverageData] =
    useState(null);

  const [savedScenarios, setSavedScenarios] =
    useState([]);

  const [savedScenarioName, setSavedScenarioName] =
    useState("");

  const [loading, setLoading] =
    useState(false);

  const [graphLoading, setGraphLoading] =
    useState(true);

  const [error, setError] =
    useState("");

  const [graphError, setGraphError] =
    useState("");

  const [dependencyError, setDependencyError] =
    useState("");

  const [coverageError, setCoverageError] =
    useState("");

  /* =======================================================
     LOAD GRAPH
     ======================================================= */

  async function loadGraph() {
    setGraphLoading(true);
    setGraphError("");

    try {
      const response = await apiFetch(
        `${API_URL}/api/graph`
      );

      if (!response.ok) {
        throw new Error(
          `Knowledge graph request failed: ${response.status}`
        );
      }

      const result = await response.json();

      if (
        !result ||
        !Array.isArray(result.nodes) ||
        !Array.isArray(result.edges)
      ) {
        throw new Error(
          "Invalid graph response"
        );
      }

      setGraphData(result);
    } catch (err) {
      console.error(
        "ATLAS graph loading error:",
        err
      );

      setGraphError(
        "The map is still connecting. You can run the scenario while it finishes loading."
      );
    } finally {
      setGraphLoading(false);
    }
  }

  /* =======================================================
     RUN SCENARIO
     ======================================================= */

  async function runScenario() {
    setLoading(true);
    setError("");

    try {
      const response = await apiFetch(
        `${API_URL}/api/scenario/explain`,
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            shock_region: shockRegion,
            shock_percent:
              Number(shockPercent),
            time_horizon_months:
              Number(horizon),
            alternate_supply_percent:
              Number(alternateSupply),
          }),
        }
      );

      if (!response.ok) {
        const errorBody =
          await response.text();

        throw new Error(errorBody);
      }

      const result =
        await response.json();

      if (
        !result ||
        !result.simulation
      ) {
        throw new Error(
          "Invalid explanation response from ATLAS."
        );
      }

      setData(result.simulation);
      setExplanation(
        result.explanation || null
      );
    } catch (err) {
      console.error(
        "ATLAS explanation/simulation error:",
        err
      );

      setError(
        "ATLAS could not run this yet. Make sure you are signed in and the backend is running."
      );
    } finally {
      setLoading(false);
    }
  }

  /* =======================================================
     LOAD DEPENDENCIES
     ======================================================= */

  async function loadDependencies() {
    setDependencyError("");

    try {
      const response = await apiFetch(
        `${API_URL}/api/data/dependencies?year=2024`
      );

      if (!response.ok) {
        throw new Error(
          `Dependency request failed: ${response.status}`
        );
      }

      const result =
        await response.json();

      setDependencyData(result);
    } catch (err) {
      console.error(
        "ATLAS dependency loading error:",
        err
      );

      setDependencyError(
        "Dependency metrics are unavailable."
      );
    }
  }

  /* =======================================================
     LOAD COVERAGE
     ======================================================= */

  async function loadCoverage() {
    try {
      const response = await apiFetch(
        `${API_URL}/api/data/coverage`
      );

      if (!response.ok) {
        throw new Error(
          `Coverage request failed: ${response.status}`
        );
      }

      setCoverageData(
        await response.json()
      );
    } catch (err) {
      console.error(
        "ATLAS coverage loading error:",
        err
      );

      setCoverageError(
        "Data coverage is unavailable."
      );
    }
  }

  /* =======================================================
     LOAD SAVED SCENARIOS
     ======================================================= */

  async function loadSavedScenarios() {
    try {
      const response = await apiFetch(
        `${API_URL}/api/scenarios`
      );

      if (!response.ok) {
        throw new Error(
          `Saved scenarios request failed: ${response.status}`
        );
      }

      setSavedScenarios(
        (await response.json()).scenarios ||
          []
      );
    } catch (err) {
      console.error(
        "ATLAS saved scenario loading error:",
        err
      );
    }
  }

  /* =======================================================
     SAVE SCENARIO
     ======================================================= */

  async function saveCurrentScenario() {
    const name =
      savedScenarioName.trim();

    if (!name) {
      setError(
        "Enter a name before saving the scenario."
      );
      return;
    }

    try {
      const response = await apiFetch(
        `${API_URL}/api/scenarios`,
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            name,
            scenario: {
              shock_region: shockRegion,
              shock_percent:
                Number(shockPercent),
              time_horizon_months:
                Number(horizon),
              alternate_supply_percent:
                Number(alternateSupply),
            },
          }),
        }
      );

      if (!response.ok) {
        throw new Error("save failed");
      }

      setSavedScenarioName("");

      await loadSavedScenarios();
    } catch (err) {
      console.error(
        "ATLAS scenario save error:",
        err
      );

      setError(
        "Unable to save the scenario."
      );
    }
  }

  /* =======================================================
     RERUN SAVED SCENARIO
     ======================================================= */

  async function rerunSavedScenario(
    saved
  ) {
    try {
      const response = await apiFetch(
        `${API_URL}/api/scenarios/${saved.id}/run`,
        {
          method: "POST",
        }
      );

      if (!response.ok) {
        throw new Error(
          "rerun failed"
        );
      }

      setData(
        await response.json()
      );

      const explanationResponse =
        await apiFetch(
          `${API_URL}/api/scenario/explain`,
          {
            method: "POST",
            headers: {
              "Content-Type":
                "application/json",
            },
            body: JSON.stringify(
              saved.scenario
            ),
          }
        );

      if (explanationResponse.ok) {
        setExplanation(
          (
            await explanationResponse.json()
          ).explanation
        );
      }
    } catch (err) {
      console.error(
        "ATLAS saved scenario rerun error:",
        err
      );

      setError(
        "Unable to rerun the saved scenario."
      );
    }
  }

  /* =======================================================
     FIREBASE AUTH STATE
     ======================================================= */

  useEffect(() => {
    if (
      !firebaseConfigured ||
      !firebaseAuth
    ) {
      setAuth(false);
      return undefined;
    }

    return onAuthStateChanged(
      firebaseAuth,
      async (user) => {
        setError("");
        setGraphError("");
        setDependencyError("");
        setCoverageError("");

        if (!user) {
          setAuth(false);
          return;
        }

        try {
          await user.getIdToken();
          setAuth({
            subject: user.uid,
            email: user.email || "",
            name:
              user.displayName ||
              user.email ||
              "ATLAS user",
            picture: user.photoURL || null,
          });
        } catch (err) {
          console.error(
            "ATLAS Firebase token initialization error:",
            err
          );
          setAuth(false);
        }
      }
    );
  }, []);

  /* =======================================================
     LOAD DATA ONLY AFTER AUTHENTICATION
     ======================================================= */

  useEffect(() => {
    if (
      auth === null ||
      auth === false
    ) {
      return;
    }

    /*
     * Firebase's auth state has now resolved.
     * Give the Firebase Auth instance a moment to
     * expose currentUser before protected API calls.
     */
    const timer = window.setTimeout(
      () => {
        loadGraph();
        loadDependencies();
        loadCoverage();
        loadSavedScenarios();
        runScenario();
      },
      0
    );

    return () =>
      window.clearTimeout(timer);
  }, [auth]);

  /* =======================================================
     DERIVED DATA
     ======================================================= */

  const shockTimeline =
    data?.comparison?.shock?.timeline ||
    [];

  const interventionTimeline =
    data?.comparison?.intervention
      ?.timeline || [];

  const baselineTimeline =
    data?.comparison?.baseline
      ?.timeline || [];

  const cascadeSummary =
    data?.comparison?.shock
      ?.cascade_summary || {};

  const latestShock =
    shockTimeline[
      shockTimeline.length - 1
    ] || {};

  const latestIntervention =
    interventionTimeline[
      interventionTimeline.length - 1
    ] || {};

  const finalPressure =
    latestShock.cascade_pressure_percent ||
    0;

  const finalInterventionPressure =
    latestIntervention
      .cascade_pressure_percent || 0;

  const interventionReduction =
    finalPressure > 0
      ? (
          (
            finalPressure -
            finalInterventionPressure
          ) /
          finalPressure
        ) * 100
      : 0;

  const timelineRows = useMemo(() => {
    return shockTimeline.map(
      (shock, index) => ({
        month: shock.month,
        activePaths:
          shock.active_path_count,
        newPaths:
          shock.new_path_count,
        nodes:
          shock.active_downstream_nodes,
        shockPressure:
          shock.cascade_pressure_percent ||
          0,
        interventionPressure:
          interventionTimeline[index]
            ?.cascade_pressure_percent ||
          0,
        averagePressure:
          shock.average_cascade_pressure_percent ||
          0,
      })
    );
  }, [
    shockTimeline,
    interventionTimeline,
  ]);

  const maxPressure = Math.max(
    ...timelineRows.map(
      (row) => row.shockPressure
    ),
    1
  );

  const explanationSteps =
    explanation?.steps ||
    explanation?.cascade_steps ||
    [];

  const explanationDrivers =
    explanation?.key_drivers || [];

  const explanationNodes =
    explanation?.affected_nodes ||
    explanation?.downstream_nodes ||
    [];

  const explanationIntervention =
    explanation?.intervention_effect ||
    {};

  const explanationUncertainty =
    explanation?.uncertainty || {};

  const explanationTraceability =
    explanation?.traceability || {};

  const selectedShockRegionLabel =
    shockRegionOptions.find(
      (option) => option.value === shockRegion
    )?.label || "Europe";

  function openDashboard(dashboard) {
    setActiveDashboard(dashboard);
    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  }

  async function askAtlas(event) {
    event.preventDefault();
    const question = assistantQuestion.trim();
    if (!question || assistantLoading) return;

    setAssistantQuestion("");
    setAssistantMessages((messages) => [
      ...messages,
      { role: "user", text: question },
    ]);
    setAssistantLoading(true);

    try {
      const response = await apiFetch(`${API_URL}/api/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question,
          context: {
            shock_region: shockRegion,
            shock_percent: shockPercent,
            time_horizon_months: horizon,
            alternate_supply_percent: alternateSupply,
          },
        }),
      });

      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.detail || "Ask ATLAS request failed.");
      }

      setAssistantMessages((messages) => [
        ...messages,
        {
          role: "assistant",
          text: result.answer,
          sources: result.sources || [],
          mode: result.mode,
        },
      ]);
    } catch (err) {
      setAssistantMessages((messages) => [
        ...messages,
        {
          role: "assistant",
          text: err.message || "Ask ATLAS could not answer right now.",
        },
      ]);
    } finally {
      setAssistantLoading(false);
    }
  }

  const dashboardContent = {
    home: {
      title: "Your food-supply picture",
      description:
        "See the latest result, the most important numbers, and what ATLAS knows.",
    },
    scenario: {
      title: "Try a what-if question",
      description:
        "Choose where a change starts, how big it is, and how much backup supply exists.",
    },
    graph: {
      title: "See the connected map",
      description:
        "Follow how food can move from producers to places that need it.",
    },
    timeline: {
      title: "Watch the story over time",
      description:
        "See which effects appear first and which effects take longer.",
    },
    reports: {
      title: "Understand the result",
      description:
        "Read the evidence, trade links, and explanation behind the simulation.",
    },
    settings: {
      title: "Your ATLAS account",
      description:
        "Your saved scenarios stay connected to your signed-in account.",
    },
  };

  /* =======================================================
     EXPORT
     ======================================================= */

  async function exportScenario(
    format
  ) {
    if (!data) return;

    try {
      const response = await apiFetch(
        `${API_URL}/api/scenario/export?format=${format}`,
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            shock_region: shockRegion,
            shock_percent:
              Number(shockPercent),
            time_horizon_months:
              Number(horizon),
            alternate_supply_percent:
              Number(alternateSupply),
          }),
        }
      );

      if (!response.ok) {
        throw new Error(
          "export failed"
        );
      }

      const blob =
        await response.blob();

      const url =
        URL.createObjectURL(blob);

      const link =
        document.createElement("a");

      link.href = url;

      link.download =
        format === "report"
          ? "atlas-scenario-report.txt"
          : "atlas-scenario.json";

      link.click();

      URL.revokeObjectURL(url);
    } catch (err) {
      console.error(
        "ATLAS export error:",
        err
      );

      setError(
        "Unable to export the current scenario."
      );
    }
  }

  /* =======================================================
     AUTH CHECK
     ======================================================= */

  if (auth === null) {
    return (
      <div className="auth-screen">
        Checking ATLAS sign-in...
      </div>
    );
  }

  /* =======================================================
     LOGIN
     ======================================================= */

  if (auth === false) {
    return (
      <div className="atlas-login">
        <div className="atlas-login__topbar">
          <div className="atlas-login__wordmark">
            <span
              className="atlas-login__leaf"
              aria-hidden="true"
            >
              ◢
            </span>

            <span>ATLAS</span>
          </div>

          <div className="atlas-login__tagline">
            <span>A SAFER</span>
            <i />
            <span>
              MORE RESILIENT
            </span>
            <i />
            <span>FOOD FUTURE</span>
          </div>
        </div>

        <main className="atlas-login__content">
          <section
            className="atlas-login__card"
            aria-label="ATLAS sign in"
          >
            <div
              className="atlas-login__globe"
              aria-hidden="true"
            >
              <div className="atlas-login__globe-ring atlas-login__globe-ring--one" />
              <div className="atlas-login__globe-ring atlas-login__globe-ring--two" />

              <div className="atlas-login__globe-core">
                <span>🌍</span>
              </div>

              <div className="atlas-login__orbit-dot atlas-login__orbit-dot--one" />
              <div className="atlas-login__orbit-dot atlas-login__orbit-dot--two" />
            </div>

            <div className="atlas-login__brand">
              ATLAS
            </div>

            <div className="atlas-login__subtitle">
              GLOBAL CONSEQUENCE SIMULATION ENGINE
            </div>

            <div className="atlas-login__divider">
              <span />
              <b>⌁</b>
              <span />
            </div>

            <p className="atlas-login__description">
              Explore how global shocks ripple
              through
              <br />
              food systems, economies and people.
            </p>

            <button
              type="button"
              className="atlas-login__google"
              disabled={!firebaseConfigured}
              onClick={async () => {
                try {
                  setError("");

                  await signInWithPopup(
                    firebaseAuth,
                    googleProvider
                  );
                } catch (err) {
                  console.error(
                    "ATLAS Firebase sign-in error:",
                    err
                  );

                  const code =
                    err?.code ||
                    "unknown";

                  const message =
                    err?.message ||
                    "Unknown Firebase error";

                  setError(
                    `Google sign-in failed: ${code} — ${message}`
                  );
                }
              }}
            >
              <span
                className="atlas-login__google-mark"
                aria-hidden="true"
              >
                G
              </span>

              <span>Continue with Google</span>

              <span
                className="atlas-login__arrow"
                aria-hidden="true"
              >
                →
              </span>
            </button>

            {error && (
              <div
                className="atlas-login__error"
                role="alert"
              >
                {error}
              </div>
            )}

            <div className="atlas-login__trust">
              <span>Secure</span>
              <b>•</b>
              <span>Fast</span>
              <b>•</b>
              <span>Trusted</span>
            </div>

            <div className="atlas-login__mini-divider">
              <span />
              <b>⌁</b>
              <span />
            </div>

            <div className="atlas-login__powered">
              Powered by Google Authentication
            </div>
          </section>
        </main>
      </div>
    );
  }

  /* =======================================================
     DASHBOARD
     ======================================================= */

  return (
    <div className="atlas-app">
      <div className="forest-bg" />

      <div className="mist mist-one" />
      <div className="mist mist-two" />

      <div className="butterfly butterfly-one">
        🦋
      </div>

      <div className="butterfly butterfly-two">
        🦋
      </div>

      <div className="butterfly butterfly-three">
        🦋
      </div>

      <div className="floating-leaf leaf-one">
        🍃
      </div>

      <div className="floating-leaf leaf-two">
        🌿
      </div>

      <button
        type="button"
        className={`ask-atlas-launcher ${assistantOpen ? "open" : ""}`}
        onClick={() => setAssistantOpen((isOpen) => !isOpen)}
        aria-label={assistantOpen ? "Close Ask ATLAS" : "Open Ask ATLAS"}
        title="Ask ATLAS"
      >
        <span aria-hidden="true">🤖</span>
        <small>Ask me</small>
      </button>

      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-icon">
            <Icon
              type="leaf"
              size={27}
            />
          </div>

          <div>
            <div className="brand-name">
              ATLAS
            </div>

            <div className="brand-subtitle">
              GLOBAL CONSEQUENCE
              <br />
              SIMULATION ENGINE
            </div>
          </div>
        </div>

        <nav className="navigation">
          <NavItem
            icon="home"
            label="Home"
            active={activeDashboard === "home"}
            onClick={() => openDashboard("home")}
          />

          <NavItem
            icon="scenario"
            label="Scenario Lab"
            active={activeDashboard === "scenario"}
            onClick={() => openDashboard("scenario")}
          />

          <NavItem
            icon="graph"
            label="Network Graph"
            active={activeDashboard === "graph"}
            onClick={() => openDashboard("graph")}
          />

          <NavItem
            icon="timeline"
            label="Timeline"
            active={activeDashboard === "timeline"}
            onClick={() => openDashboard("timeline")}
          />

          <NavItem
            icon="report"
            label="Reports"
            active={activeDashboard === "reports"}
            onClick={() => openDashboard("reports")}
          />

          <NavItem
            icon="settings"
            label="Settings"
            active={activeDashboard === "settings"}
            onClick={() => openDashboard("settings")}
          />
        </nav>

        <div className="sidebar-bottom">
          <div className="planet-message">
            <span>“</span>
            A more resilient
            <br />
            food system
            <br />
            builds a healthier
            <br />
            planet.
            <span>”</span>
          </div>

          <div className="sidebar-leaves">
            🍃 🌱
          </div>
        </div>
      </aside>

      <main
        className={`main-content dashboard-${activeDashboard}`}
      >
        <header className="top-header">
          <div className="mobile-brand">
            <Icon
              type="leaf"
              size={23}
            />
            ATLAS
          </div>

          <div className="online-status">
            <span className="online-dot" />
            Simulation Engine Online
          </div>

          <div className="profile">
            <div
              className="avatar"
              aria-label={`${auth.name} avatar`}
            >
              {getUserInitials(
                auth.name,
                auth.email
              )}
            </div>

            <div className="profile-text">
              <strong>
                {auth.name}
              </strong>

              <small>
                {auth.email}
              </small>
            </div>

            <span className="profile-arrow">
              <button
                type="button"
                className="logout-button"
                onClick={async () => {
                  try {
                    await signOut(
                      firebaseAuth
                    );

                    setAuth(false);
                  } catch (err) {
                    console.error(
                      "ATLAS Firebase logout error:",
                      err
                    );

                    setError(
                      "Unable to sign out."
                    );
                  }
                }}
              >
                Log out
              </button>
            </span>
          </div>
        </header>

        <section className="dashboard-intro">
          <div className="section-label">
            {activeDashboard.toUpperCase()} DASHBOARD
          </div>

          <h2>
            {dashboardContent[activeDashboard].title}
          </h2>

          <p>
            {dashboardContent[activeDashboard].description}
          </p>
        </section>

        {assistantOpen && (
        <section className="ask-atlas-panel ask-atlas-popover">
          <button
            type="button"
            className="ask-atlas-close"
            onClick={() => setAssistantOpen(false)}
            aria-label="Close Ask ATLAS"
          >
            ×
          </button>
          <div className="ask-atlas-heading">
            <div>
              <div className="section-label">ASK ATLAS / LIVE RESEARCH</div>
              <h2>What are you curious about?</h2>
              <p>
                Ask in your own words. ATLAS checks public information and
                explains what it can prove, what it assumes, and where to read more.
              </p>
            </div>
            <div className="ask-atlas-badge">
              <Icon type="shield" size={16} />
              SOURCE-AWARE
            </div>
          </div>

          <div className="ask-atlas-messages" aria-live="polite">
            {assistantMessages.map((message, index) => (
              <div
                className={`ask-atlas-message ${message.role}`}
                key={`${message.role}-${index}`}
              >
                <span className="ask-atlas-message-label">
                  {message.role === "user" ? "YOU" : "ATLAS"}
                </span>
                <p>{message.text}</p>
                {message.sources?.length > 0 && (
                  <div className="ask-atlas-sources">
                    {message.sources.slice(0, 3).map((source) => (
                      <a
                        href={source.url}
                        target="_blank"
                        rel="noreferrer"
                        key={source.url}
                      >
                        {source.title}
                      </a>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {assistantLoading && (
              <div className="ask-atlas-message assistant">
                <span className="ask-atlas-message-label">ATLAS</span>
                <p>Looking through public sources...</p>
              </div>
            )}
          </div>

          <form className="ask-atlas-form" onSubmit={askAtlas}>
            <input
              value={assistantQuestion}
              onChange={(event) => setAssistantQuestion(event.target.value)}
              placeholder="Example: Why can a wheat shortage affect bread prices?"
              aria-label="Ask ATLAS a question"
              maxLength={500}
            />
            <button type="submit" disabled={assistantLoading || !assistantQuestion.trim()}>
              <Icon type="chat" size={17} />
              Ask
            </button>
          </form>
        </section>
        )}

        <section
          id="atlas-home"
          className="hero-section dashboard-view dashboard-home"
        >
          <div className="hero-copy">
            <div className="section-label">
              ◦ START HERE / WHEAT SUPPLY
            </div>

            <h1>
              See what happens when{" "}
              <span>
                food supply changes
              </span>
              <br />
              around the world.
            </h1>

            <p>
              Choose a place, choose how big the
              change is, and ATLAS will show you
              who may be affected over time.
            </p>
          </div>

          <div className="earth-orbit">
            <div className="earth">
              <div className="earth-land land-one" />
              <div className="earth-land land-two" />
              <div className="earth-land land-three" />

              <div className="earth-glow" />

              <div className="earth-node node-one" />
              <div className="earth-node node-two" />
              <div className="earth-node node-three" />
              <div className="earth-node node-four" />

              <div className="earth-connection connection-one" />
              <div className="earth-connection connection-two" />
              <div className="earth-connection connection-three" />
            </div>

            <div className="orbit-ring ring-one" />
            <div className="orbit-ring ring-two" />
          </div>

          <div className="model-card">
            <span>MODEL VERSION</span>

            <strong>
              {data?.model?.version ||
                "0.6.0"}
            </strong>

            <small>
              PROVISIONAL DEMO
            </small>
          </div>

          <div className="healthy-message">
            Healthy Food
            <br />
            Healthy Planet{" "}
            <span>🍃</span>
          </div>
        </section>

        {error && (
          <div className="error-message">
            <strong>
              ENGINE CONNECTION ERROR
            </strong>

            <span>{error}</span>
          </div>
        )}

        {graphError && (
          <div className="error-message">
            <strong>
              MAP STILL LOADING
            </strong>

            <span>
              {graphError}
            </span>
          </div>
        )}

        <section
          id="atlas-scenario"
          className="controls-grid dashboard-view dashboard-scenario"
        >
          <ControlCard
            number="01"
            label="1 / WHERE?"
            title="Choose a place"
            icon="wheat"
            value={`${shockPercent}%`}
          >
            <div className="control-field-label">
              <span>
                Where does the change start?
              </span>
            </div>

            <label className="region-select">
              <span>🌍</span>
              <select
                aria-label="Shock region"
                value={shockRegion}
                onChange={(event) =>
                  setShockRegion(event.target.value)
                }
              >
                {shockRegionOptions.map((option) => (
                  <option
                    key={option.value}
                    value={option.value}
                  >
                    {option.label}
                  </option>
                ))}
              </select>
              <span aria-hidden="true">⌄</span>
            </label>

            <div className="control-field-label production-label">
              <span>
                Production shock
              </span>

              <strong>
                {shockPercent}%
              </strong>
            </div>

            <input
              className="nature-slider"
              type="range"
              min="-50"
              max="-5"
              step="5"
              value={shockPercent}
              onChange={(event) =>
                setShockPercent(
                  Number(
                    event.target.value
                  )
                )
              }
            />

            <div className="slider-endpoints">
              <span>-50%</span>
              <span>-5%</span>
            </div>
          </ControlCard>

          <ControlCard
            number="02"
            label="2 / WHEN?"
            title="Choose a time"
            icon="calendar"
            value={`${horizon} months`}
          >
            <div className="control-field-label horizon-label">
              <span>
                How far ahead should we look?
              </span>

              <strong>
                {horizon} months
              </strong>
            </div>

            <input
              className="nature-slider"
              type="range"
              min="1"
              max="36"
              step="1"
              value={horizon}
              onChange={(event) =>
                setHorizon(
                  Number(
                    event.target.value
                  )
                )
              }
            />

            <div className="slider-endpoints">
              <span>1 month</span>
              <span>36 months</span>
            </div>

            <div className="card-decoration butterfly-mini">
              🦋
            </div>
          </ControlCard>

          <ControlCard
            number="03"
            label="3 / HELP"
            title="Add backup supply"
            icon="leaf"
            value={`+${alternateSupply}%`}
          >
            <div className="control-field-label">
              <span>
                How much backup is available?
              </span>

              <strong>
                +{alternateSupply}%
              </strong>
            </div>

            <input
              className="nature-slider"
              type="range"
              min="0"
              max="50"
              step="5"
              value={alternateSupply}
              onChange={(event) =>
                setAlternateSupply(
                  Number(
                    event.target.value
                  )
                )
              }
            />

            <div className="slider-endpoints">
              <span>0%</span>
              <span>50%</span>
            </div>

            <div className="card-decoration plant-mini">
              🌱
            </div>
          </ControlCard>
        </section>

        <section className="run-section dashboard-view dashboard-scenario">
          <button
            className="run-button"
            onClick={runScenario}
            disabled={loading}
          >
            <Icon
              type="leaf"
              size={19}
            />

            {loading
              ? "SIMULATING..."
              : "SHOW ME WHAT HAPPENS"}

            <span className="run-arrow">
              →
            </span>
          </button>

          <div className="scenario-path">
            <Icon
              type="leaf"
              size={14}
            />

            {selectedShockRegionLabel} → North Africa

            <span>•</span>

            Wheat

            <span>•</span>

            {horizon} month horizon
          </div>

          <div className="scenario-save-row">
            <input
              className="scenario-save-input"
              value={savedScenarioName}
              onChange={(event) =>
                setSavedScenarioName(
                  event.target.value
                )
              }
              placeholder="Name this scenario"
              aria-label="Saved scenario name"
            />

            <button
              type="button"
              className="scenario-button"
              onClick={
                saveCurrentScenario
              }
            >
              Save scenario
            </button>
          </div>
        </section>

        {savedScenarios.length > 0 && (
          <section className="saved-scenarios-panel dashboard-view dashboard-scenario">
            <div className="section-label">
              MY SAVED SCENARIOS
            </div>

            <div className="saved-scenarios-list">
              {savedScenarios.map(
                (saved) => (
                  <button
                    type="button"
                    className="saved-scenario-item"
                    key={saved.id}
                    onClick={() =>
                      rerunSavedScenario(
                        saved
                      )
                    }
                  >
                    <strong>
                      {saved.name}
                    </strong>

                    <span>
                      {
                        saved.scenario
                          .shock_percent
                      }{" "}
                      ·{" "}
                      {
                        saved.scenario
                          .time_horizon_months
                      }{" "}
                      months
                    </span>
                  </button>
                )
              )}
            </div>
          </section>
        )}

        <section className="metrics-layout dashboard-view dashboard-home">
          <Metric
            icon="network"
            label="ACTIVE CASCADE PATHS"
            value={
              cascadeSummary.cascade_paths ||
              0
            }
            detail={`${
              cascadeSummary.max_order ||
              0
            } maximum propagation order`}
          />

          <Metric
            icon="network"
            label="DOWNSTREAM NODES"
            value={
              cascadeSummary.affected_downstream_nodes ||
              0
            }
            detail="Potentially affected graph nodes"
          />

          <Metric
            icon="chart"
            label="PEAK CASCADE PRESSURE"
            value={`${formatNumber(
              finalPressure,
              2
            )}%`}
            detail={`Month ${
              latestShock.month ||
              "—"
            }`}
          />

          <div className="metric-card baseline-metric">
            <div className="metric-icon">
              <Icon
                type="leaf"
                size={21}
              />
            </div>

            <div>
              <span>BASELINE</span>

              <strong>
                {formatNumber(
                  baselineTimeline[
                    baselineTimeline.length -
                      1
                  ]
                    ?.cascade_pressure_percent,
                  1
                )}
                %
              </strong>

              <small>
                No-shock reference state
              </small>
            </div>
          </div>
        </section>

        <section
          id="atlas-reports"
          className="dependency-panel dashboard-view dashboard-reports"
        >
          <div className="timeline-header">
            <div>
              <div className="section-label">
                05 / OBSERVED TRADE DEPENDENCY
              </div>

              <h2>
                Supplier concentration
              </h2>

              <p>
                Descriptive 2024 supplier
                shares from observed trade
                records. Missing observations
                are not treated as zero.
              </p>
            </div>

            <span className="data-status-badge">
              DATA-DERIVED
            </span>
          </div>

          {dependencyError && (
            <div className="inline-data-error">
              {dependencyError}
            </div>
          )}

          <div className="dependency-grid">
            {(
              dependencyData?.metrics ||
              []
            )
              .slice(0, 6)
              .map((metric) => (
                <div
                  className="dependency-card"
                  key={
                    metric.importer
                  }
                >
                  <strong>
                    {metric.importer}
                  </strong>

                  <span>
                    {
                      metric.active_supplier_count
                    }{" "}
                    observed suppliers
                  </span>

                  <small>
                    HHI{" "}
                    {formatNumber(
                      metric.supplier_concentration_hhi,
                      3
                    )}
                  </small>

                  <div className="supplier-list">
                    {metric.top_suppliers
                      .slice(0, 3)
                      .map(
                        (
                          supplier
                        ) => (
                          <span
                            key={
                              supplier.supplier
                            }
                          >
                            {
                              supplier.supplier
                            }
                            :{" "}
                            {formatNumber(
                              supplier.share *
                                100,
                              1
                            )}
                            %
                          </span>
                        )
                      )}
                  </div>
                </div>
              ))}
          </div>
        </section>

        <section className="dependency-panel coverage-panel dashboard-view dashboard-reports">
          <div className="timeline-header">
            <div>
              <div className="section-label">
                06 / DATA COVERAGE
              </div>

              <h2>
                Evidence status
              </h2>

              <p>
                Observed coverage is separated
                from unavailable and provisional
                domains.
              </p>
            </div>

            <span className="data-status-badge">
              PROVENANCE
            </span>
          </div>

          {coverageError && (
            <div className="inline-data-error">
              {coverageError}
            </div>
          )}

          <div className="coverage-grid">
            {(
              coverageData?.datasets ||
              []
            ).map((dataset) => (
              <div
                className="coverage-card"
                key={dataset.name}
              >
                <strong>
                  {dataset.name}
                </strong>

                <span>
                  {dataset.status}
                </span>

                <small>
                  {(
                    dataset.years || []
                  ).join(", ") ||
                    "No validated years"}
                </small>
              </div>
            ))}

            {Object.entries(
              coverageData?.layers || {}
            ).map(
              ([name, layer]) => (
                <div
                  className="coverage-card"
                  key={name}
                >
                  <strong>
                    {name}
                  </strong>

                  <span>
                    {layer.status}
                  </span>

                  <small>
                    {layer.limitations?.[0] ||
                      "See provenance endpoint."}
                  </small>
                </div>
              )
            )}
          </div>
        </section>

        <section
          id="atlas-graph"
          className="atlas-graph-wrapper dashboard-view dashboard-graph"
        >
          <ButterflyMap
            graph={graphData}
            simulation={data}
          />

          {graphLoading && (
            <div className="graph-loading-overlay">
              <div className="graph-loading-spinner" />

              <strong>
                Loading Knowledge Graph
              </strong>

              <span>
                Connecting ATLAS dependency
                network...
              </span>
            </div>
          )}
        </section>

        <section
          id="atlas-timeline"
          className="timeline-section dashboard-view dashboard-timeline"
        >
          <div className="timeline-header">
            <div>
              <div className="section-label">
                04 / TEMPORAL PROPAGATION
              </div>

              <h2>
                Cascade Timeline
              </h2>

              <p>
                Watch consequences activate as
                propagation delays accumulate
                across the dependency graph.
              </p>
            </div>

            <div className="timeline-legend">
              <span>
                <i className="legend blue" />
                Shock
              </span>

              <span>
                <i className="legend green" />
                Intervention
              </span>
            </div>
          </div>

          <div className="timeline-layout">
            <div className="timeline-chart">
              <div className="chart-y-axis">
                <span>150%</span>
                <span>100%</span>
                <span>50%</span>
                <span>0%</span>
              </div>

              <div className="chart-area">
                <div className="grid-line line-150" />
                <div className="grid-line line-100" />
                <div className="grid-line line-50" />
                <div className="grid-line line-0" />

                <div className="timeline-columns">
                  {timelineRows.map(
                    (row) => {
                      const shockHeight =
                        (row.shockPressure /
                          maxPressure) *
                        100;

                      const interventionHeight =
                        (row.interventionPressure /
                          maxPressure) *
                        100;

                      return (
                        <div
                          className="timeline-column"
                          key={row.month}
                        >
                          <div className="column-bars">
                            <div
                              className="timeline-bar shock"
                              style={{
                                height: `${Math.max(
                                  4,
                                  shockHeight
                                )}%`,
                              }}
                            >
                              <span>
                                {formatNumber(
                                  row.shockPressure,
                                  2
                                )}
                                %
                              </span>
                            </div>

                            <div
                              className="timeline-bar intervention"
                              style={{
                                height: `${Math.max(
                                  4,
                                  interventionHeight
                                )}%`,
                              }}
                            >
                              <span>
                                {formatNumber(
                                  row.interventionPressure,
                                  2
                                )}
                                %
                              </span>
                            </div>
                          </div>

                          <small>
                            Month{" "}
                            {row.month}
                          </small>
                        </div>
                      );
                    }
                  )}
                </div>
              </div>
            </div>

            <div className="timeline-insights">
              <div className="insight-title">
                MONTH 1 → {horizon}
              </div>

              <Insight
                icon="network"
                label="Active paths"
                value={`${
                  timelineRows[0]
                    ?.activePaths || 0
                } → ${
                  latestShock.active_path_count ||
                  0
                }`}
              />

              <Insight
                icon="leaf"
                label="New paths"
                value={`${
                  timelineRows[0]
                    ?.newPaths || 0
                } → ${
                  latestShock.new_path_count ||
                  0
                }`}
              />

              <Insight
                icon="network"
                label="Downstream nodes"
                value={`${
                  timelineRows[0]?.nodes ||
                  0
                } → ${
                  latestShock.active_downstream_nodes ||
                  0
                }`}
              />

              <Insight
                icon="chart"
                label="Avg. cascade pressure"
                value={`${formatNumber(
                  timelineRows[0]
                    ?.averagePressure,
                  2
                )}% → ${formatNumber(
                  latestShock
                    .average_cascade_pressure_percent,
                  2
                )}%`}
              />
            </div>
          </div>
        </section>

        {explanation && (
          <section
            className="atlas-explanation-section dashboard-view dashboard-reports"
            style={{
              marginTop: "42px",
              padding: "30px",
              borderRadius: "24px",
              border:
                "1px solid rgba(123, 182, 135, 0.22)",
              background:
                "linear-gradient(145deg, rgba(19, 45, 35, 0.88), rgba(10, 29, 24, 0.94))",
              boxShadow:
                "0 20px 60px rgba(0, 0, 0, 0.22)",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent:
                  "space-between",
                alignItems:
                  "flex-start",
                gap: "24px",
                marginBottom:
                  "26px",
                flexWrap:
                  "wrap",
              }}
            >
              <div>
                <div className="section-label">
                  05 / EXPLAINABLE CASCADE
                </div>

                <h2
                  style={{
                    margin:
                      "8px 0 8px",
                    fontSize:
                      "32px",
                  }}
                >
                  Why the ripple spreads
                </h2>

                <p
                  style={{
                    maxWidth:
                      "760px",
                    margin: 0,
                    color:
                      "rgba(230, 244, 235, 0.68)",
                    lineHeight:
                      1.7,
                  }}
                >
                  The explanation below is
                  generated from the deterministic
                  simulation results. It describes
                  modeled propagation pathways rather
                  than a validated real-world forecast.
                </p>
              </div>

              <div
                style={{
                  display: "flex",
                  alignItems:
                    "center",
                  gap: "9px",
                  padding:
                    "10px 14px",
                  borderRadius:
                    "999px",
                  background:
                    "rgba(121, 184, 132, 0.09)",
                  border:
                    "1px solid rgba(121, 184, 132, 0.2)",
                  color:
                    "#a9d8b1",
                  fontSize:
                    "12px",
                  fontWeight:
                    700,
                  letterSpacing:
                    "0.08em",
                }}
              >
                <Icon
                  type="shield"
                  size={15}
                />
                TRACEABLE MODEL EXPLANATION
              </div>

              <div
                style={{
                  display: "flex",
                  gap: "8px",
                }}
              >
                <button
                  type="button"
                  className="scenario-button secondary"
                  onClick={() =>
                    exportScenario(
                      "json"
                    )
                  }
                >
                  Export JSON
                </button>

                <button
                  type="button"
                  className="scenario-button secondary"
                  onClick={() =>
                    exportScenario(
                      "report"
                    )
                  }
                >
                  Export report
                </button>
              </div>
            </div>

            {(explanation.summary ||
              explanation.headline) && (
              <div
                style={{
                  padding:
                    "20px 22px",
                  borderRadius:
                    "18px",
                  background:
                    "rgba(255, 255, 255, 0.035)",
                  border:
                    "1px solid rgba(255, 255, 255, 0.07)",
                  marginBottom:
                    "22px",
                }}
              >
                <div
                  style={{
                    fontSize:
                      "11px",
                    letterSpacing:
                      "0.12em",
                    fontWeight:
                      800,
                    color:
                      "#8fc99a",
                    marginBottom:
                      "9px",
                  }}
                >
                  MODEL SUMMARY
                </div>

                <div
                  style={{
                    fontSize:
                      "17px",
                    lineHeight:
                      1.65,
                    color:
                      "#e4f1e7",
                  }}
                >
                  {explanation.summary ||
                    explanation.headline}
                </div>
              </div>
            )}

            <div
              style={{
                display:
                  "grid",
                gridTemplateColumns:
                  "repeat(auto-fit, minmax(240px, 1fr))",
                gap:
                  "16px",
                marginBottom:
                  "26px",
              }}
            >
              <ExplanationStat
                icon="network"
                label="CASCADE PATHS"
                value={
                  cascadeSummary.cascade_paths ||
                  0
                }
                detail="Modeled propagation pathways"
              />

              <ExplanationStat
                icon="timeline"
                label="PROPAGATION ORDER"
                value={
                  cascadeSummary.max_order ||
                  0
                }
                detail="Maximum modeled order"
              />

              <ExplanationStat
                icon="network"
                label="DOWNSTREAM REACH"
                value={
                  cascadeSummary.affected_downstream_nodes ||
                  0
                }
                detail="Affected graph nodes"
              />

              <ExplanationStat
                icon="chart"
                label="LATEST ACTIVATION"
                value={`${cascadeSummary.latest_activation_month || 0}M`}
                detail="Latest modeled activation"
              />
            </div>

            {explanationSteps.length >
              0 && (
              <div
                style={{
                  marginBottom:
                    "28px",
                }}
              >
                <ExplanationHeading
                  number="01"
                  title="Propagation pathway"
                  subtitle="How the modeled shock activates downstream dependencies over time."
                />

                <div
                  style={{
                    display:
                      "flex",
                    flexDirection:
                      "column",
                    gap:
                      "10px",
                  }}
                >
                  {explanationSteps.map(
                    (
                      step,
                      index
                    ) => (
                      <div
                        key={`cascade-step-${index}`}
                        style={{
                          display:
                            "grid",
                          gridTemplateColumns:
                            "58px 1fr auto",
                          gap:
                            "16px",
                          alignItems:
                            "center",
                          padding:
                            "17px 18px",
                          borderRadius:
                            "16px",
                          background:
                            "rgba(255,255,255,0.025)",
                          border:
                            "1px solid rgba(255,255,255,0.06)",
                        }}
                      >
                        <div
                          style={{
                            width:
                              "42px",
                            height:
                              "42px",
                            borderRadius:
                              "50%",
                            display:
                              "grid",
                            placeItems:
                              "center",
                            background:
                              "rgba(121,184,132,0.1)",
                            color:
                              "#9ed0a7",
                            fontWeight:
                              800,
                            fontSize:
                              "13px",
                          }}
                        >
                          {String(
                            step.order ??
                              index +
                                1
                          ).padStart(
                            2,
                            "0"
                          )}
                        </div>

                        <div>
                          <div
                            style={{
                              fontSize:
                                "14px",
                              fontWeight:
                                750,
                              color:
                                "#e5f1e7",
                              marginBottom:
                                "5px",
                            }}
                          >
                            {step.path ||
                              step.description ||
                              step.title ||
                              "Modeled cascade step"}
                          </div>

                          {step.description &&
                            step.path && (
                              <div
                                style={{
                                  color:
                                    "rgba(230,244,235,0.58)",
                                  fontSize:
                                    "12px",
                                  lineHeight:
                                    1.5,
                                }}
                              >
                                {
                                  step.description
                                }
                              </div>
                            )}
                        </div>

                        <div
                          style={{
                            minWidth:
                              "74px",
                            textAlign:
                              "right",
                          }}
                        >
                          <div
                            style={{
                              fontSize:
                                "10px",
                              color:
                                "rgba(230,244,235,0.42)",
                              letterSpacing:
                                "0.08em",
                            }}
                          >
                            ACTIVATION
                          </div>

                          <strong
                            style={{
                              color:
                                "#a8d8b0",
                              fontSize:
                                "14px",
                            }}
                          >
                            Month{" "}
                            {step.activation_month ??
                              step.month ??
                              "—"}
                          </strong>
                        </div>
                      </div>
                    )
                  )}
                </div>
              </div>
            )}

            {explanationDrivers.length >
              0 && (
              <div
                style={{
                  marginBottom:
                    "28px",
                }}
              >
                <ExplanationHeading
                  number="02"
                  title="Key drivers"
                  subtitle="Simulation quantities that contribute to the modeled cascade."
                />

                <div
                  style={{
                    display:
                      "grid",
                    gridTemplateColumns:
                      "repeat(auto-fit, minmax(220px, 1fr))",
                    gap:
                      "12px",
                  }}
                >
                  {explanationDrivers.map(
                    (
                      driver,
                      index
                    ) => (
                      <div
                        key={`driver-${index}`}
                        style={{
                          padding:
                            "18px",
                          borderRadius:
                            "16px",
                          background:
                            "rgba(255,255,255,0.025)",
                          border:
                            "1px solid rgba(255,255,255,0.06)",
                        }}
                      >
                        <div
                          style={{
                            color:
                              "#9fd2a8",
                            fontSize:
                              "11px",
                            fontWeight:
                              800,
                            letterSpacing:
                              "0.08em",
                            marginBottom:
                              "8px",
                          }}
                        >
                          {String(
                            driver.label ||
                              driver.name ||
                              "DRIVER"
                          ).toUpperCase()}
                        </div>

                        <strong
                          style={{
                            display:
                              "block",
                            color:
                              "#edf7ef",
                            fontSize:
                              "20px",
                            marginBottom:
                              "7px",
                          }}
                        >
                          {driver.value !==
                          undefined
                            ? typeof driver.value ===
                              "number"
                              ? formatNumber(
                                  driver.value,
                                  2
                                )
                              : driver.value
                            : "—"}
                        </strong>

                        <span
                          style={{
                            color:
                              "rgba(230,244,235,0.55)",
                            fontSize:
                              "12px",
                            lineHeight:
                              1.5,
                          }}
                        >
                          {driver.description ||
                            driver.detail ||
                            "Model-derived cascade driver."}
                        </span>
                      </div>
                    )
                  )}
                </div>
              </div>
            )}

            {explanationNodes.length >
              0 && (
              <div
                style={{
                  marginBottom:
                    "28px",
                }}
              >
                <ExplanationHeading
                  number="03"
                  title="Downstream effects"
                  subtitle="Graph nodes reached by the modeled propagation."
                />

                <div
                  style={{
                    display:
                      "grid",
                    gridTemplateColumns:
                      "repeat(auto-fit, minmax(220px, 1fr))",
                    gap:
                      "12px",
                  }}
                >
                  {explanationNodes.map(
                    (
                      node,
                      index
                    ) => (
                      <div
                        key={`node-${index}`}
                        style={{
                          padding:
                            "17px",
                          borderRadius:
                            "16px",
                          background:
                            "rgba(255,255,255,0.025)",
                          border:
                            "1px solid rgba(255,255,255,0.06)",
                        }}
                      >
                        <div
                          style={{
                            fontWeight:
                              750,
                            color:
                              "#e6f2e9",
                            marginBottom:
                              "6px",
                          }}
                        >
                          {node.name ||
                            node.node ||
                            node.id ||
                            "Downstream node"}
                        </div>

                        <div
                          style={{
                            fontSize:
                              "12px",
                            color:
                              "rgba(230,244,235,0.54)",
                            lineHeight:
                              1.5,
                          }}
                        >
                          {node.description ||
                            node.effect ||
                            node.role ||
                            "Reached through the modeled dependency graph."}
                        </div>
                      </div>
                    )
                  )}
                </div>
              </div>
            )}

            <div
              style={{
                display:
                  "grid",
                gridTemplateColumns:
                  "repeat(auto-fit, minmax(260px, 1fr))",
                gap:
                  "16px",
                marginBottom:
                  "26px",
              }}
            >
              <div
                style={{
                  padding:
                    "20px",
                  borderRadius:
                    "18px",
                  background:
                    "rgba(87, 156, 103, 0.07)",
                  border:
                    "1px solid rgba(113, 181, 125, 0.15)",
                }}
              >
                <div
                  style={{
                    color:
                      "#91c99a",
                    fontSize:
                      "10px",
                    letterSpacing:
                      "0.1em",
                    fontWeight:
                      800,
                    marginBottom:
                      "9px",
                  }}
                >
                  INTERVENTION EFFECT
                </div>

                <strong
                  style={{
                    display:
                      "block",
                    fontSize:
                      "28px",
                    color:
                      "#b1dfb8",
                    marginBottom:
                      "6px",
                  }}
                >
                  {formatNumber(
                    explanationIntervention
                      .supply_loss_reduction_percent ??
                      interventionReduction,
                    1
                  )}
                  %
                </strong>

                <div
                  style={{
                    fontSize:
                      "12px",
                    color:
                      "rgba(230,244,235,0.57)",
                    lineHeight:
                      1.55,
                  }}
                >
                  {explanationIntervention.summary ||
                    `A +${alternateSupply}% alternate-supply intervention is modeled against the same shock scenario.`}
                </div>
              </div>

              <div
                style={{
                  padding:
                    "20px",
                  borderRadius:
                    "18px",
                  background:
                    "rgba(255, 194, 102, 0.045)",
                  border:
                    "1px solid rgba(255, 194, 102, 0.12)",
                }}
              >
                <div
                  style={{
                    color:
                      "#d9b879",
                    fontSize:
                      "10px",
                    letterSpacing:
                      "0.1em",
                    fontWeight:
                      800,
                    marginBottom:
                      "9px",
                  }}
                >
                  UNCERTAINTY
                </div>

                <strong
                  style={{
                    display:
                      "block",
                    fontSize:
                      "16px",
                    color:
                      "#ead7ad",
                    marginBottom:
                      "7px",
                  }}
                >
                  {explanationUncertainty.level ||
                    explanationUncertainty.label ||
                    "Provisional"}
                </strong>

                <div
                  style={{
                    fontSize:
                      "12px",
                    color:
                      "rgba(230,244,235,0.57)",
                    lineHeight:
                      1.55,
                  }}
                >
                  {explanationUncertainty.description ||
                    explanationUncertainty.summary ||
                    explanationUncertainty.message ||
                    "Outputs depend on provisional demonstration inputs and deterministic model assumptions."}
                </div>
              </div>
            </div>

            <div
              style={{
                padding:
                  "19px 21px",
                borderRadius:
                  "17px",
                background:
                  "rgba(255,255,255,0.025)",
                border:
                  "1px solid rgba(255,255,255,0.06)",
              }}
            >
              <div
                style={{
                  display:
                    "flex",
                  alignItems:
                    "center",
                  gap:
                    "10px",
                  marginBottom:
                    "12px",
                }}
              >
                <Icon
                  type="shield"
                  size={18}
                />

                <strong
                  style={{
                    fontSize:
                      "13px",
                    color:
                      "#dcebe0",
                    letterSpacing:
                      "0.05em",
                  }}
                >
                  TRACEABILITY & ASSUMPTIONS
                </strong>
              </div>

              <div
                style={{
                  display:
                    "grid",
                  gap:
                    "7px",
                  color:
                    "rgba(230,244,235,0.58)",
                  fontSize:
                    "12px",
                  lineHeight:
                    1.55,
                }}
              >
                {explanationTraceability
                  .simulation_engine_version && (
                  <div>
                    <strong
                      style={{
                        color:
                          "rgba(230,244,235,0.82)",
                      }}
                    >
                      Simulation Engine:
                    </strong>{" "}
                    {
                      explanationTraceability.simulation_engine_version
                    }
                  </div>
                )}

                {explanationTraceability
                  .explanation_engine_version && (
                  <div>
                    <strong
                      style={{
                        color:
                          "rgba(230,244,235,0.82)",
                      }}
                    >
                      Explanation Engine:
                    </strong>{" "}
                    {
                      explanationTraceability.explanation_engine_version
                    }
                  </div>
                )}

                {explanationTraceability
                  .method && (
                  <div>
                    <strong
                      style={{
                        color:
                          "rgba(230,244,235,0.82)",
                      }}
                    >
                      Method:
                    </strong>{" "}
                    {
                      explanationTraceability.method
                    }
                  </div>
                )}

                {explanationTraceability
                  .data_status && (
                  <div>
                    <strong
                      style={{
                        color:
                          "rgba(230,244,235,0.82)",
                      }}
                    >
                      Data:
                    </strong>{" "}
                    {
                      explanationTraceability.data_status
                    }
                  </div>
                )}

                {explanationTraceability
                  .llm_used !==
                  undefined && (
                  <div>
                    <strong
                      style={{
                        color:
                          "rgba(230,244,235,0.82)",
                      }}
                    >
                      LLM Used:
                    </strong>{" "}
                    {explanationTraceability.llm_used
                      ? "Yes"
                      : "No"}
                  </div>
                )}

                {!explanationTraceability
                  .simulation_engine_version &&
                  !explanationTraceability
                    .explanation_engine_version &&
                  !explanationTraceability
                    .method &&
                  !explanationTraceability
                    .data_status && (
                    <div>
                      This explanation is derived
                      directly from the deterministic
                      ATLAS simulation output.
                      Demonstration inputs are
                      provisional and the model is not
                      a validated forecast.
                    </div>
                  )}
              </div>
            </div>
          </section>
        )}

        <section className="scenario-cards dashboard-view dashboard-reports">
          <ScenarioCard
            title="BASELINE"
            subtitle="No-shock reference state"
            timeline={
              baselineTimeline
            }
            value={
              baselineTimeline[
                baselineTimeline.length -
                  1
              ]
                ?.cascade_pressure_percent ||
              0
            }
            type="baseline"
          />

          <ScenarioCard
            title="SHOCK"
            subtitle={`${shockPercent}% Europe production shock`}
            timeline={
              shockTimeline
            }
            value={
              finalPressure
            }
            type="shock"
          />

          <ScenarioCard
            title="INTERVENTION"
            subtitle={`+${alternateSupply}% alternate supply`}
            timeline={
              interventionTimeline
            }
            value={
              finalInterventionPressure
            }
            type="intervention"
          />
        </section>

        <section className="comparison-summary dashboard-view dashboard-reports">
          <div className="comparison-summary-icon">
            🌱
          </div>

          <div>
            <span>
              INTERVENTION EFFECT
            </span>

            <strong>
              {formatNumber(
                Math.max(
                  0,
                  interventionReduction
                ),
                1
              )}
              % pressure reduction
            </strong>

            <small>
              Compared with the same shock
              scenario without alternate supply.
            </small>
          </div>
        </section>

        <section
          id="atlas-settings"
          className="settings-panel dashboard-view dashboard-settings"
        >
          <div className="section-label">
            SETTINGS / YOUR ATLAS
          </div>

          <h2>
            Your private workspace
          </h2>

          <p>
            You are signed in as {auth.name}. Your
            saved scenarios belong to your account and
            are not shown to other users.
          </p>

          <div className="settings-summary">
            <span>Signed-in account</span>
            <strong>{auth.email}</strong>
          </div>
        </section>

        <footer className="dashboard-footer">
          <div>
            <Icon
              type="leaf"
              size={16}
            />
            ATLAS
          </div>

          <span>
            Deterministic scenario model ·
            Data-derived metrics · Not a validated
            forecast
          </span>

          <span>
            Model{" "}
            {data?.model?.version ||
              "0.6.0"}
          </span>
        </footer>
      </main>
    </div>
  );
}

/* =========================================================
   EXPLANATION COMPONENTS
   ========================================================= */

function ExplanationHeading({
  number,
  title,
  subtitle,
}) {
  return (
    <div
      style={{
        marginBottom:
          "14px",
      }}
    >
      <div
        style={{
          display:
            "flex",
          alignItems:
            "center",
          gap:
            "10px",
          marginBottom:
            "5px",
        }}
      >
        <span
          style={{
            fontSize:
              "10px",
            fontWeight:
              800,
            letterSpacing:
              "0.12em",
            color:
              "#80bc8c",
          }}
        >
          {number}
        </span>

        <h3
          style={{
            margin: 0,
            fontSize:
              "18px",
            color:
              "#e3efe5",
          }}
        >
          {title}
        </h3>
      </div>

      <p
        style={{
          margin: 0,
          fontSize:
            "12px",
          color:
            "rgba(230,244,235,0.48)",
          lineHeight:
            1.5,
        }}
      >
        {subtitle}
      </p>
    </div>
  );
}

function ExplanationStat({
  icon,
  label,
  value,
  detail,
}) {
  return (
    <div
      style={{
        display:
          "flex",
        gap:
          "14px",
        alignItems:
          "center",
        padding:
          "17px",
        borderRadius:
          "16px",
        background:
          "rgba(255,255,255,0.025)",
        border:
          "1px solid rgba(255,255,255,0.06)",
      }}
    >
      <div
        style={{
          width:
            "40px",
          height:
            "40px",
          borderRadius:
            "13px",
          display:
            "grid",
          placeItems:
            "center",
          background:
            "rgba(111, 177, 124, 0.09)",
          color:
            "#9ed0a7",
          flexShrink:
            0,
        }}
      >
        <Icon
          type={icon}
          size={19}
        />
      </div>

      <div>
        <span
          style={{
            display:
              "block",
            fontSize:
              "9px",
            fontWeight:
              800,
            letterSpacing:
              "0.1em",
            color:
              "rgba(230,244,235,0.45)",
            marginBottom:
              "3px",
          }}
        >
          {label}
        </span>

        <strong
          style={{
            display:
              "block",
            fontSize:
              "20px",
            color:
              "#e5f1e7",
          }}
        >
          {value}
        </strong>

        <small
          style={{
            color:
              "rgba(230,244,235,0.45)",
            fontSize:
              "10px",
          }}
        >
          {detail}
        </small>
      </div>
    </div>
  );
}

/* =========================================================
   NAV
   ========================================================= */

function NavItem({
  icon,
  label,
  active,
  onClick,
}) {
  return (
    <button
      type="button"
      className={`nav-item ${
        active ? "active" : ""
      }`}
      onClick={onClick}
      aria-current={active ? "page" : undefined}
    >
      <Icon
        type={icon}
        size={18}
      />
      <span>{label}</span>
    </button>
  );
}

/* =========================================================
   CONTROL CARD
   ========================================================= */

function ControlCard({
  number,
  label,
  title,
  icon,
  value,
  children,
}) {
  return (
    <div className="control-card">
      <div className="control-card-top">
        <div className="control-title">
          <div className="control-icon">
            <Icon
              type={icon}
              size={21}
            />
          </div>

          <div>
            <div className="section-label">
              {number} / {label}
            </div>

            <h3>{title}</h3>
          </div>
        </div>

        <strong className="control-value">
          {value}
        </strong>
      </div>

      <div className="control-body">
        {children}
      </div>
    </div>
  );
}

/* =========================================================
   METRIC
   ========================================================= */

function Metric({
  icon,
  label,
  value,
  detail,
}) {
  return (
    <div className="metric-card">
      <div className="metric-icon">
        <Icon
          type={icon}
          size={21}
        />
      </div>

      <div>
        <span>{label}</span>

        <strong>{value}</strong>

        <small>{detail}</small>
      </div>

      <div className="metric-leaf">
        🍃
      </div>
    </div>
  );
}

/* =========================================================
   INSIGHT
   ========================================================= */

function Insight({
  icon,
  label,
  value,
}) {
  return (
    <div className="insight">
      <div className="insight-icon">
        <Icon
          type={icon}
          size={19}
        />
      </div>

      <div>
        <span>{label}</span>

        <strong>{value}</strong>
      </div>
    </div>
  );
}

/* =========================================================
   SCENARIO CARD
   ========================================================= */

function ScenarioCard({
  title,
  subtitle,
  timeline,
  value,
  type,
}) {
  const max = Math.max(
    ...timeline.map(
      (item) =>
        item.cascade_pressure_percent ||
        0
    ),
    1
  );

  return (
    <div
      className={`scenario-card ${type}`}
    >
      <div className="scenario-card-heading">
        <div>
          <div className="scenario-name">
            {title}
          </div>

          <p>{subtitle}</p>
        </div>

        <strong>
          {formatNumber(
            value,
            1
          )}
          %
        </strong>
      </div>

      <div className="mini-chart">
        {timeline.map(
          (item) => (
            <div
              className="mini-column"
              key={item.month}
            >
              <div
                className="mini-bar"
                style={{
                  height: `${Math.max(
                    5,
                    (
                      (item.cascade_pressure_percent ||
                        0) /
                      max
                    ) *
                      100
                  )}%`,
                }}
              />

              <span>
                {item.month}
              </span>
            </div>
          )
        )}
      </div>
    </div>
  );
}

export default App;