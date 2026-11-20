import React from "react";
import { createRoot } from "react-dom/client";
import { App, type Bootstrap } from "./App";
import "./styles.css";

const element = document.getElementById("app-data");
const root = document.getElementById("root");
if (!element || !root) throw new Error("Faltan los datos de la aplicación");

const data = JSON.parse(element.textContent || "{}") as Bootstrap;
createRoot(root).render(
  <React.StrictMode>
    <App data={data} />
  </React.StrictMode>,
);
