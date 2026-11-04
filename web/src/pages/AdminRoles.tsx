import { Check, Minus } from "lucide-react";

import { useRoleMatrix } from "../api/hooks";
import { Empty, Panel, SkeletonRows } from "../components/ui";

/** Read-only view of permissions.py: the role ladder and who can do what. */
export function AdminRoles() {
  const { data, isLoading, isError } = useRoleMatrix();

  if (isError) {
    return (
      <Panel>
        <Empty title="Could not load roles" message="Please refresh and try again." />
      </Panel>
    );
  }
  if (isLoading || !data) {
    return (
      <Panel>
        <SkeletonRows count={8} />
      </Panel>
    );
  }

  const ladder = [...data.roles].sort((a, b) => b.level - a.level);

  return (
    <div className="management-workspace roles-workspace">
      <section className="ladder stagger" aria-label="Role hierarchy">
        {ladder.map((role) => (
          <div key={role.key} className={`ladder-step role-${role.key}`}>
            <span className="ladder-level">L{role.level}</span>
            <span className="ladder-mark">{monogram(role.label)}</span>
            <span className="ladder-name">{role.label}</span>
            <span className="ladder-note">{role.scoped ? "Own department" : "Whole workspace"}</span>
          </div>
        ))}
      </section>

      <Panel flush title="Permission matrix">
        <div className="table-wrap">
          <table className="matrix">
            <thead>
              <tr>
                <th scope="col">Permission</th>
                {ladder.map((role) => (
                  <th scope="col" key={role.key} className={`matrix-role role-${role.key}`}>
                    {role.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="stagger">
              {data.permissions.map((permission) => (
                <tr key={permission.key}>
                  <th scope="row">
                    <div className="cell-primary">{permission.label}</div>
                    <div className="cell-secondary mono">{permission.key}</div>
                  </th>
                  {ladder.map((role) => {
                    const granted = permission.roles.includes(role.key);
                    return (
                      <td key={role.key} className="matrix-cell">
                        {granted ? (
                          <span className={`matrix-yes role-${role.key}`} title={role.scoped ? "Own department" : "Everyone"}>
                            <Check aria-label="Allowed" />
                          </span>
                        ) : (
                          <Minus className="matrix-no" aria-label="Not allowed" />
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <div className="rule-cards stagger">
        <div className="rule-card">
          <strong>No escalation.</strong> You can only grant roles, and only change accounts, ranked
          below your own.
        </div>
        <div className="rule-card">
          <strong>Department scope.</strong> Managers and team leads only see and manage people and
          work inside their own department.
        </div>
        <div className="rule-card">
          <strong>Separate door.</strong> Admins sign in through the console; their sessions end
          after 30 idle minutes.
        </div>
      </div>
    </div>
  );
}

/** "Super admin" → "SA", "Admin" → "AD". */
function monogram(label: string) {
  const words = label.split(" ");
  return (words.length > 1 ? words.map((w) => w[0]).join("") : label.slice(0, 2)).toUpperCase();
}
