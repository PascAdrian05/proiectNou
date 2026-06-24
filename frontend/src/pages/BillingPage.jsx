import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { billingService } from "../services/api/billingService";

const PLANS = [
  {
    id: "free",
    name: "Free",
    price: "€0",
    period: "forever",
    features: ["Up to 3 websites", "Weekly scans", "Email alerts", "Basic reports"],
    cta: null,
  },
  {
    id: "basic",
    name: "Basic",
    price: "€19",
    period: "/month",
    features: ["Up to 10 websites", "Daily scans", "Priority alerts", "CSV & PDF exports", "Shareable reports"],
    cta: "Upgrade to Basic",
  },
  {
    id: "pro",
    name: "Pro",
    price: "€49",
    period: "/month",
    features: ["Unlimited websites", "Hourly scans", "Behavior risk scoring", "Custom branding", "Stripe billing portal"],
    cta: "Upgrade to Pro",
    highlight: true,
  },
];

export function BillingPage() {
  const { auth } = useAuth();
  const toast = useToast();
  const [searchParams] = useSearchParams();
  const [subscription, setSubscription] = useState(null);
  const [error, setError] = useState("");
  const [isBusy, setIsBusy] = useState(true);
  const [actionPlan, setActionPlan] = useState("");

  async function loadSubscription() {
    setError("");
    setIsBusy(true);
    try {
      const data = await billingService.getSubscription();
      setSubscription(data);
    } catch (loadError) {
      setError(loadError.message || "Could not load subscription");
    } finally {
      setIsBusy(false);
    }
  }

  useEffect(() => {
    loadSubscription();
  }, []);

  useEffect(() => {
    const status = searchParams.get("status");
    if (status === "success") {
      toast.success("Subscription updated successfully.");
      loadSubscription();
    } else if (status === "cancel") {
      toast.info("Checkout was cancelled.");
    }
  }, [searchParams]);

  async function onUpgrade(plan) {
    setActionPlan(plan);
    setError("");
    try {
      const data = await billingService.createCheckoutSession(plan);
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      }
    } catch (upgradeError) {
      setError(upgradeError.message || "Could not start checkout");
      toast.error(upgradeError.message || "Could not start checkout");
    } finally {
      setActionPlan("");
    }
  }

  async function onManageBilling() {
    setError("");
    setIsBusy(true);
    try {
      const data = await billingService.openPortal();
      if (data.portal_url) {
        window.location.href = data.portal_url;
      }
    } catch (portalError) {
      setError(portalError.message || "Could not open billing portal");
      toast.error(portalError.message || "Could not open billing portal");
    } finally {
      setIsBusy(false);
    }
  }

  const currentPlan = subscription?.plan || "free";
  const periodEnd = subscription?.current_period_end
    ? new Date(subscription.current_period_end).toLocaleDateString()
    : null;

  return (
    <section className="page-card">
      <div className="list-header">
        <div>
          <h2>Billing & Plans</h2>
          <p className="hint">Manage your subscription and upgrade monitoring capacity.</p>
        </div>
        {subscription?.stripe_customer_id && (
          <button type="button" onClick={onManageBilling} disabled={isBusy}>
            Manage in Stripe
          </button>
        )}
      </div>

      {error && <p className="error-text">{error}</p>}
      {isBusy && !subscription && <p className="route-loader">Loading subscription...</p>}

      {subscription && (
        <div className="billing-current">
          <article className="stat-card stat-card-accent">
            <p className="stat-label">Current plan</p>
            <p className="stat-value">{currentPlan.toUpperCase()}</p>
            <p className="hint">
              Status: {subscription.status}
              {periodEnd && ` · Renews ${periodEnd}`}
            </p>
            <p className="hint">Tenant: {auth.tenantId || "n/a"} · Role: {auth.role || "n/a"}</p>
          </article>
        </div>
      )}

      <div className="plan-grid">
        {PLANS.map((plan) => {
          const isCurrent = currentPlan === plan.id;
          const isUpgrade = plan.cta && !isCurrent;

          return (
            <article key={plan.id} className={`plan-card${plan.highlight ? " plan-card-highlight" : ""}${isCurrent ? " plan-card-current" : ""}`}>
              {plan.highlight && <span className="plan-badge">Popular</span>}
              {isCurrent && <span className="plan-badge plan-badge-current">Current</span>}
              <h3>{plan.name}</h3>
              <p className="plan-price">
                {plan.price}
                <span className="plan-period">{plan.period}</span>
              </p>
              <ul className="plan-features">
                {plan.features.map((feature) => (
                  <li key={feature}>{feature}</li>
                ))}
              </ul>
              {isUpgrade && (
                <button
                  type="button"
                  className={plan.highlight ? "plan-cta-primary" : ""}
                  onClick={() => onUpgrade(plan.id)}
                  disabled={Boolean(actionPlan)}
                >
                  {actionPlan === plan.id ? "Redirecting..." : plan.cta}
                </button>
              )}
              {isCurrent && plan.id === "free" && (
                <p className="hint">You're on the free tier. Upgrade anytime.</p>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
