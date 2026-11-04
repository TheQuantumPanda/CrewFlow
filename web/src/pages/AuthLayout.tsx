import { CrewFlowBrand } from "../components/Brand";
import { Activity, ShieldCheck, Split, Workflow } from "lucide-react";
import type { ReactNode } from "react";

const POINTS = [
  { icon: Workflow, text: "Assign work and watch it move across the board" },
  { icon: Split, text: "Seven roles, each seeing exactly what it should" },
  { icon: ShieldCheck, text: "Every change captured in an audit log" },
];

const FLOATING = [
  { code: "CF-142", title: "Migrate payroll exports", state: "In progress", tone: "teal", progress: 64 },
  { code: "CF-139", title: "Quarterly access review", state: "Pending", tone: "amber" },
  { code: "CF-131", title: "Onboard design team", state: "Done", tone: "ember", done: true },
];

/**
 * Split auth layout. The dark side carries the brand: slowly turning orbit
 * rings and a few task cards bobbing in place, so the page feels alive
 * without anything competing with the form.
 */
export function AuthLayout({
  headline,
  accent,
  lede,
  children,
}: {
  headline: string;
  accent: string;
  lede: string;
  children: ReactNode;
}) {
  return (
    <div className="auth">
      <aside className="auth-aside">
        <Orbits />

        <div className="auth-brand rise">
          <CrewFlowBrand />
        </div>

        <div className="auth-hero">
          <span className="live-pill rise d1">
            <span className="live-dot" />
            Workspace online
          </span>
          <h1 className="auth-headline rise d2">
            {headline} <em>{accent}</em>
          </h1>
          <p className="auth-lede rise d3">{lede}</p>

          <div className="auth-points rise d4">
            {POINTS.map(({ icon: Icon, text }) => (
              <div className="auth-point" key={text}>
                <Icon />
                <span>{text}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="float-stack" aria-hidden="true">
          {FLOATING.map((card, i) => (
            <div className={`float-card float-${i}`} key={card.code}>
              <div className="float-card-head">
                <span className="mono">{card.code}</span>
                <span className={`tone tone-${card.tone}`}>{card.state}</span>
              </div>
              <div className={`float-card-title${card.done ? " done" : ""}`}>{card.title}</div>
              {card.progress ? (
                <div className="float-meter">
                  <span style={{ width: `${card.progress}%` }} />
                </div>
              ) : null}
            </div>
          ))}
        </div>

        <div className="auth-foot rise d5">
          <Activity size={14} aria-hidden="true" /> Keep teams and work in sync.
        </div>
      </aside>

      <main className="auth-main">{children}</main>
    </div>
  );
}

export function Orbits() {
  return (
    <svg className="orbits" viewBox="0 0 760 760" fill="none" aria-hidden="true">
      <g className="orbit-slow">
        <circle cx="380" cy="380" r="370" stroke="currentColor" strokeDasharray="4 10" />
        <circle cx="750" cy="380" r="7" className="orbit-dot-ember" />
        <circle cx="10" cy="380" r="5" className="orbit-dot-teal" />
      </g>
      <g className="orbit-rev">
        <circle cx="380" cy="380" r="250" stroke="currentColor" strokeDasharray="1 8" />
        <circle cx="380" cy="130" r="6" className="orbit-dot-amber" />
      </g>
    </svg>
  );
}

type DemoAccount = { role: string; username: string; password: string };

export const WORKSPACE_DEMOS: DemoAccount[] = [
  { role: "HR", username: "neha.kapoor", password: "Hr@12345" },
  { role: "Manager", username: "priya.mehta", password: "Manager@123" },
  { role: "Team lead", username: "vikram.rao", password: "Lead@1234" },
  { role: "Employee", username: "aarav.sharma", password: "Employee@123" },
  { role: "Auditor", username: "isha.menon", password: "Audit@123" },
];

export const CONSOLE_DEMOS: DemoAccount[] = [
  { role: "Super admin", username: "ayush.yadav", password: "Ayush@123" },
  { role: "Admin", username: "meera.nair", password: "Admin@123" },
];

/**
 * Demo logins, shown only when the build opts in via VITE_DEMO_MODE. A real
 * deploy mints a random admin password at bootstrap, so printing fixed
 * credentials there would be both wrong and a giveaway.
 */
export function DemoAccounts({
  accounts,
  onPick,
}: {
  accounts: DemoAccount[];
  onPick: (username: string, password: string) => void;
}) {
  if (import.meta.env.VITE_DEMO_MODE !== "true") return null;

  return (
    <div className="demo-box">
      <div className="demo-box-title">Demo accounts</div>
      {accounts.map((account) => (
        <div className="demo-row" key={account.username}>
          <span>{account.role}</span>
          <code>{account.username}</code>
          <button
            type="button"
            className="demo-fill"
            onClick={() => onPick(account.username, account.password)}
          >
            Use
          </button>
        </div>
      ))}
    </div>
  );
}
