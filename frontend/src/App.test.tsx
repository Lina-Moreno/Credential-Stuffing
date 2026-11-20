import { afterEach, describe, expect, it } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { Login, Monitor, type Attempt, type Metric } from "./App";

afterEach(cleanup);

const manual: Attempt[] = [
  { id: "manual-2", time: "2026-11-19T12:01:00-05:00", account: "usuario_02",
    source: "localhost", success: false, score: null, alert: null },
  { id: "manual-1", time: "2026-11-19T12:00:00-05:00", account: "usuario_01",
    source: "localhost", success: true, score: 0.03, alert: false },
];
const simulated: Attempt[] = [
  { id: "sim-2", time: "2026-11-19T12:02:00+00:00", account: "usuario_05",
    source: "198.51.100.2", success: true, score: 0.18, alert: true,
    origins_account: 3, related_origins: 4 },
  { id: "sim-1", time: "2026-11-19T12:01:00+00:00", account: "usuario_06",
    source: "192.0.2.5", success: false, score: 0.02, alert: false,
    origins_account: 1, related_origins: 0 },
];
const metrics: Metric[] = [
  { method: "contador_origen", TP: 2, FP: 1, TN: 7, FN: 2, precision: 2 / 3, recall: 0.5, F1: 4 / 7 },
  { method: "isolation_forest", TP: 3, FP: 2, TN: 6, FN: 1, precision: 0.6, recall: 0.75, F1: 2 / 3 },
];
const props = { page: "monitor" as const, manual, simulated, metrics,
  summary: { evaluated: 12, alerts: 5, false_alerts: 2 }, threshold: 0.12, has_image: true };

describe("monitor de accesos", () => {
  it("keeps credential and detector decisions separate, including unscored rows", () => {
    render(<Monitor {...props} />);
    const ring = screen.getByTestId("status-ring");
    expect(within(ring).getByText("Sin evaluar")).toBeTruthy();
    const manualRow = screen.getByRole("row", { name: /usuario_02/ });
    expect(within(manualRow).getByText("Inválida")).toBeTruthy();
    expect(within(manualRow).getByText("Sin evaluar")).toBeTruthy();
    fireEvent.click(screen.getByRole("row", { name: /usuario_01/ }));
    expect(within(ring).getByText("Sin alerta")).toBeTruthy();
    expect(screen.getByText("0.0300")).toBeTruthy();
  });

  it("resets selection on tab change and shows the selected row's observations", () => {
    render(<Monitor {...props} />);
    fireEvent.click(screen.getByRole("tab", { name: /Última simulación/ }));
    const ring = screen.getByTestId("status-ring");
    expect(within(ring).getByText("Alerta")).toBeTruthy();
    expect(screen.getByText("0.1800")).toBeTruthy();
    expect(screen.getByText("0.1200")).toBeTruthy();
    expect(screen.getByText((_, element) => element?.tagName === "P" &&
      element.textContent?.includes("3 orígenes distintos") === true)).toBeTruthy();
    fireEvent.click(screen.getByRole("row", { name: /usuario_06/ }));
    expect(within(ring).getByText("Sin alerta")).toBeTruthy();
    expect(screen.getByText("0.0200")).toBeTruthy();
    fireEvent.click(screen.getByRole("tab", { name: /Intentos manuales/ }));
    expect(within(ring).getByText("Sin evaluar")).toBeTruthy();
  });

  it("filters alerts and uses the stored model summary", () => {
    render(<Monitor {...props} />);
    expect(within(screen.getByText("Intentos evaluados").closest("article")!).getByText("12")).toBeTruthy();
    expect(within(screen.getByText("Alertas del modelo").closest("article")!).getByText("5")).toBeTruthy();
    expect(within(screen.getByText("Falsas alertas").closest("article")!).getByText("2")).toBeTruthy();
    fireEvent.click(screen.getByRole("tab", { name: /Última simulación/ }));
    fireEvent.click(screen.getByRole("checkbox", { name: "Solo alertas" }));
    expect(within(document.querySelector(".attempt-table")!).getAllByRole("row").length).toBe(2);
    expect(screen.getByRole("row", { name: /usuario_05/ })).toBeTruthy();
  });
});

describe("login", () => {
  it("posts the existing Flask fields and displays the result", () => {
    render(<Login message="Acceso rechazado" />);
    const form = document.querySelector("form");
    expect(form?.getAttribute("method")).toBe("post");
    expect(form?.getAttribute("action")).toBe("/");
    expect(screen.getByLabelText("Usuario").getAttribute("name")).toBe("username");
    expect(screen.getByLabelText("Contraseña").getAttribute("name")).toBe("password");
    expect(screen.getByRole("status").textContent).toBe("Acceso rechazado");
  });
});
