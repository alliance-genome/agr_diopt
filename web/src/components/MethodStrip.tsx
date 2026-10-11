import type { CSSProperties } from "react";
import type { Pair } from "../types";
import { methodState, methodsLabel } from "../format";

type StripProps = { pair: Pair; columns: string[]; covered: Set<string> };
const gridStyle = (n: number) => ({ "--method-count": n }) as CSSProperties;
const stateClass = (s: string) => s.replace(/ /g, "-");

export function MethodHeader({ columns }: { columns: string[] }) {
  return (
    <span className="method-grid method-names" aria-hidden="true" style={gridStyle(columns.length)}>
      {columns.map((name) => <span key={name}>{name}</span>)}
    </span>
  );
}

export function MethodCells({ pair, columns, covered }: StripProps) {
  return (
    <span className="method-grid" style={gridStyle(columns.length)}>
      {columns.map((name) => {
        const state = methodState(name, pair, covered);
        return (
          <span
            key={name}
            role="img"
            className={`method-cell ${stateClass(state)}`}
            aria-label={`${name}: ${state}`}
            title={`${name}: ${state}`}
          />
        );
      })}
    </span>
  );
}

export function MobileMethods({ pair, columns, covered }: StripProps) {
  return (
    <details className="methods-mobile">
      <summary>{methodsLabel(pair, columns, covered)}</summary>
      <ul>
        {columns.map((name) => {
          const state = methodState(name, pair, covered);
          return <li key={name} className={stateClass(state)}>{name}: {state}</li>;
        })}
      </ul>
    </details>
  );
}
