import React from "react";

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    // Surface to the console so the user (and Claude) can see exactly
    // what blew up instead of the page silently disappearing.
    // eslint-disable-next-line no-console
    console.error("App crashed:", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: "2rem", maxWidth: 720, margin: "2rem auto" }}>
          <h2 style={{ marginTop: 0 }}>Something went wrong</h2>
          <p>The page crashed before it could render. Here is the error:</p>
          <pre
            style={{
              background: "#1f2937",
              color: "#f9fafb",
              padding: "1rem",
              borderRadius: 8,
              overflowX: "auto",
              whiteSpace: "pre-wrap",
            }}
          >
            {String(this.state.error?.stack || this.state.error || "Unknown error")}
          </pre>
          <button
            type="button"
            onClick={() => window.location.reload()}
            style={{
              marginTop: "1rem",
              padding: "0.6rem 1rem",
              borderRadius: 8,
              background: "var(--accent)",
              color: "#fff",
              border: "none",
              cursor: "pointer",
              fontWeight: 600,
            }}
          >
            Reload page
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}