import { useState } from "react";

export type Attempt = {
  id: string;
  time: string;
  account: string;
  source: string;
  success: boolean;
  score: number | null;
  alert: boolean | null;
  origins_account?: number;
  related_origins?: number;
};

export type Metric = {
  method: string;
  TP: number;
  FP: number;
  TN: number;
  FN: number;
  precision: number | null;
  recall: number | null;
  F1: number | null;
};

type Summary = { evaluated: number; alerts: number; false_alerts: number };
export type Bootstrap =
  | { page: "login"; message: string | null }
  | { page: "monitor"; manual: Attempt[]; simulated: Attempt[];
      metrics: Metric[]; summary: Summary | null; threshold: number | null;
      has_image: boolean };

const number = (value: number) => new Intl.NumberFormat("es-CO").format(value);

function timeLabel(value: string) {
  const [date, clock = ""] = value.split("T");
  return `${date} ${clock.slice(0, 8)}${value.endsWith("+00:00") ? " UTC" : ""}`;
}

function detectorState(row: Attempt): "alert" | "quiet" | "unscored" {
  if (row.score === null || row.alert === null) return "unscored";
  return row.alert ? "alert" : "quiet";
}

function detectorText(row: Attempt) {
  const state = detectorState(row);
  return state === "alert" ? "Alerta" : state === "quiet" ? "Sin alerta" : "Sin evaluar";
}

function Badge({ tone, children }: { tone: string; children: string }) {
  return <span className={`badge badge--${tone}`}>{children}</span>;
}

export function Login({ message }: { message: string | null }) {
  return (
    <main className="login-layout">
      <div className="login-stack">
        <div className="brand brand--center"><span className="brand-mark" aria-hidden="true">M</span><span>Monitor de accesos</span></div>
        <section className="login-card" aria-labelledby="login-title">
          <div className="login-icon" aria-hidden="true"><LockIcon /></div>
          <p className="eyebrow">ACCESO LOCAL · LABORATORIO</p>
          <h1 id="login-title">Iniciar sesión</h1>
          <p className="muted login-description">Ingresa tus credenciales para registrar un intento de acceso</p>
          {message && <div role="status" className={`login-message ${message === "Acceso concedido" ? "login-message--ok" : "login-message--error"}`}>{message}</div>}
          <form method="post" action="/" className="login-form">
            <label htmlFor="username">Usuario</label>
            <input id="username" name="username" type="text" autoComplete="username" required maxLength={80} placeholder="usuario_01" />
            <label htmlFor="password">Contraseña</label>
            <input id="password" name="password" type="password" autoComplete="current-password" required placeholder="Ingresa tu contraseña" />
            <button className="primary-button" type="submit">Iniciar sesión</button>
          </form>
          <div className="login-footer"><a href="/resultados">Ver monitor de accesos</a></div>
        </section>
        <p className="login-caption">El detector observa y alerta. La contraseña decide el acceso.</p>
      </div>
    </main>
  );
}

function LockIcon() {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/><path d="M12 15v2"/></svg>;
}

function StatCard({ title, value, detail, tone }: { title: string; value: number | null; detail: string; tone?: string }) {
  return <article className={`stat-card ${tone ? `stat-card--${tone}` : ""}`}>
    <p className="stat-label">{title}</p>
    <strong className="stat-value">{value === null ? "—" : number(value)}</strong>
    <p className="stat-detail">{detail}</p>
  </article>;
}

function AttemptTable({ rows, selectedId, onSelect, simulated }: {
  rows: Attempt[]; selectedId: string | null; onSelect: (id: string) => void; simulated: boolean;
}) {
  return <div className="table-scroll">
    <table className="attempt-table">
      <thead><tr><th>Hora</th><th>Usuario</th><th>Origen</th><th>Credencial</th><th>Detector</th></tr></thead>
      <tbody>{rows.map((row) => <tr key={row.id} className={row.id === selectedId ? "selected-row" : ""}
        tabIndex={0} aria-selected={row.id === selectedId} onClick={() => onSelect(row.id)}
        onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onSelect(row.id); } }}>
        <td className="time-cell" title={row.time}>{timeLabel(row.time)}</td>
        <td className="account-cell">{row.account}</td>
        <td className="source-cell">{row.source}{simulated && <span className="synthetic-tag">sintético</span>}</td>
        <td><Badge tone={row.success ? "valid" : "invalid"}>{row.success ? "Válida" : "Inválida"}</Badge></td>
        <td><Badge tone={detectorState(row)}>{detectorText(row)}</Badge></td>
      </tr>)}</tbody>
    </table>
  </div>;
}

export function AttemptAnalysis({ row, simulated, threshold }: {
  row: Attempt | null; simulated: boolean; threshold: number | null;
}) {
  const state = row ? detectorState(row) : "empty";
  return <aside className="panel analysis-panel" aria-labelledby="analysis-title">
    <div className="panel-heading"><p className="eyebrow">DETALLE DEL EVENTO</p><h2 id="analysis-title">Análisis del intento</h2></div>
    <div className={`ring ring--${state}`} data-testid="status-ring" aria-label={row ? `Detector: ${detectorText(row)}` : "Sin selección"}>
      <div className="ring-inner">
        <span className="ring-kicker">DETECTOR</span>
        <strong>{row ? detectorText(row) : "Sin selección"}</strong>
      </div>
    </div>
    {row ? <>
      <p className="analysis-note">Decisión registrada para este intento. El puntaje mide anomalía, no probabilidad de fraude.</p>
      <dl className="detail-list">
        <div><dt>Usuario</dt><dd>{row.account}</dd></div>
        <div><dt>Origen</dt><dd>{row.source}</dd></div>
        <div><dt>Credencial</dt><dd>{row.success ? "Válida" : "Inválida"}</dd></div>
        <div><dt>Puntaje de anomalía</dt><dd>{row.score === null ? "No disponible" : row.score.toFixed(4)}</dd></div>
        {simulated && <div><dt>Umbral aplicado</dt><dd>{threshold === null ? "No disponible" : threshold.toFixed(4)}</dd></div>}
      </dl>
      {simulated && row.origins_account !== undefined && row.related_origins !== undefined &&
        <div className="observations"><h3>Contexto observado · 5 minutos previos</h3>
          <p><strong>{number(row.origins_account)}</strong> orígenes distintos intentaron acceder a esta cuenta.</p>
          <p><strong>{number(row.related_origins)}</strong> otros orígenes visitaron cuentas en común con este origen.</p>
          <small>Estas observaciones ayudan a describir el evento; no son una explicación exacta del bosque.</small>
        </div>}
    </> : <p className="analysis-empty">Selecciona un intento para ver el detalle.</p>}
  </aside>;
}

const PAGE_SIZE = 12;

export function Monitor({ manual, simulated, metrics, summary, threshold, has_image }: Extract<Bootstrap, { page: "monitor" }>) {
  const [tab, setTab] = useState<"manual" | "simulated">("manual");
  const [onlyAlerts, setOnlyAlerts] = useState(false);
  const [page, setPage] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const allRows = tab === "manual" ? manual : simulated;
  const filtered = onlyAlerts ? allRows.filter((row) => detectorState(row) === "alert") : allRows;
  const maxPage = Math.max(0, Math.ceil(filtered.length / PAGE_SIZE) - 1);
  const currentPage = Math.min(page, maxPage);
  const pageRows = filtered.slice(currentPage * PAGE_SIZE, (currentPage + 1) * PAGE_SIZE);
  const selected = pageRows.find((row) => row.id === selectedId) ?? pageRows[0] ?? null;

  function changeTab(next: "manual" | "simulated") {
    setTab(next); setOnlyAlerts(false); setPage(0); setSelectedId(null);
  }
  function changeAlertFilter() {
    setOnlyAlerts(!onlyAlerts); setPage(0); setSelectedId(null);
  }
  function changePage(next: number) {
    setPage(next); setSelectedId(null);
  }

  return <main className="monitor-layout">
    <header className="monitor-header">
      <div><div className="brand"><span className="brand-mark" aria-hidden="true">M</span><span>MONITOR / LABORATORIO</span></div>
        <h1>Monitor de accesos</h1><p>Detección de actividad inusual en el inicio de sesión</p></div>
      <a className="outline-button" href="/">Probar login</a>
    </header>

    <section aria-labelledby="summary-title" className="summary-section">
      <div className="section-label"><span className="section-index">01</span><h2 id="summary-title">Resumen de la última simulación</h2></div>
      {summary === null && <div className="empty-notice">Aún no hay resultados de simulación. Ejecuta <code>.venv/bin/python demo.py</code> y recarga esta página.</div>}
      <div className="stats-grid">
        <StatCard title="Intentos evaluados" value={summary?.evaluated ?? null} detail="Eventos de prueba simulados" />
        <StatCard title="Alertas del modelo" value={summary?.alerts ?? null} detail="Verdaderos positivos + falsas alertas" tone="amber" />
        <StatCard title="Falsas alertas" value={summary?.false_alerts ?? null} detail="Legítimos señalados por el modelo" />
      </div>
    </section>

    <section aria-labelledby="records-title" className="records-section">
      <div className="section-label"><span className="section-index">02</span><h2 id="records-title">Registros de acceso</h2></div>
      <div className="records-layout">
        <div className="panel table-panel">
          <div className="table-toolbar">
            <div className="tabs" role="tablist" aria-label="Fuente de intentos">
              <button type="button" role="tab" aria-selected={tab === "manual"} onClick={() => changeTab("manual")}>Intentos manuales <span>{number(manual.length)}</span></button>
              <button type="button" role="tab" aria-selected={tab === "simulated"} onClick={() => changeTab("simulated")}>Última simulación <span>{number(simulated.length)}</span></button>
            </div>
            <label className="filter-control"><input type="checkbox" checked={onlyAlerts} onChange={changeAlertFilter} /> Solo alertas</label>
          </div>
          <div className="table-caption"><span>{tab === "manual" ? "Intentos del formulario local" : "Eventos sintéticos de prueba · IP ficticias"}</span><span>{number(filtered.length)} registros</span></div>
          {pageRows.length > 0 ? <AttemptTable rows={pageRows} selectedId={selected?.id ?? null} onSelect={setSelectedId} simulated={tab === "simulated"} /> :
            <div className="table-empty">{onlyAlerts ? "No hay alertas en esta lista." : tab === "manual" ? <>Aún no hay intentos manuales. <a href="/">Probar login</a></> : <>Aún no hay simulación. Ejecuta <code>.venv/bin/python demo.py</code>.</>}</div>}
          <div className="table-pagination"><span>Página {filtered.length ? currentPage + 1 : 0} de {filtered.length ? maxPage + 1 : 0}</span><div>
            <button type="button" onClick={() => changePage(currentPage - 1)} disabled={currentPage === 0}>Anterior</button>
            <button type="button" onClick={() => changePage(currentPage + 1)} disabled={currentPage >= maxPage}>Siguiente</button>
          </div></div>
        </div>
        <AttemptAnalysis row={selected} simulated={tab === "simulated"} threshold={threshold} />
      </div>
    </section>

    <section aria-labelledby="experiment-title" className="experiment-section">
      <div className="section-label"><span className="section-index">03</span><h2 id="experiment-title">Resultados del experimento</h2></div>
      <p className="section-description">Comparación sobre los mismos eventos de prueba. El detector solo genera alertas; no decide si la credencial es válida.</p>
      <div className="experiment-grid">
        <div className="panel comparison-panel"><h3>Comparación de métodos</h3>
          {metrics.length ? <div className="table-scroll"><table className="metrics-table"><thead><tr><th>Método</th><th>TP</th><th>FP</th><th>TN</th><th>FN</th><th>Precisión</th><th>Recall</th><th>F1</th></tr></thead><tbody>
            {metrics.map((item) => <tr key={item.method}><td>{item.method === "isolation_forest" ? "Isolation Forest" : item.method === "contador_origen" ? "Contador por origen" : item.method}</td><td>{item.TP}</td><td>{item.FP}</td><td>{item.TN}</td><td>{item.FN}</td><td>{item.precision === null ? "No calculable" : item.precision.toFixed(3)}</td><td>{item.recall === null ? "No calculable" : item.recall.toFixed(3)}</td><td>{item.F1 === null ? "No calculable" : item.F1.toFixed(3)}</td></tr>)}
          </tbody></table></div> : <p className="muted">Ejecuta la demo para generar la comparación.</p>}
        </div>
        <div className="panel matrix-panel"><h3>Matriz de confusión · Isolation Forest</h3>
          {has_image ? <img src="/matriz_confusion.png" alt="Matriz de confusión del modelo con ejes Real y Predicho" /> : <p className="muted">La matriz aparecerá después de ejecutar la demo.</p>}
        </div>
      </div>
    </section>
    <footer className="monitor-footer">Demo local · datos simulados para el experimento · sin bloqueo automático</footer>
  </main>;
}

export function App({ data }: { data: Bootstrap }) {
  return data.page === "login" ? <Login message={data.message} /> : <Monitor {...data} />;
}
