from fastapi import APIRouter
from fastapi.responses import HTMLResponse


router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def web_home():
    return """
<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <title>Calcolo Quote - MVP</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      margin: 0;
      background: #eef2f7;
      color: #1f2937;
    }
    .page {
      max-width: 1240px;
      margin: 0 auto;
      padding: 24px;
    }
    .hero {
      background: #111827;
      color: white;
      border-radius: 12px;
      padding: 22px;
      margin-bottom: 16px;
    }
    .hero p {
      color: #d1d5db;
      margin: 8px 0 0;
    }
    h1, h2, h3 {
      margin-bottom: 8px;
    }
    h1 {
      margin-top: 0;
    }
    section {
      background: white;
      border: 1px solid #e5e7eb;
      border-radius: 12px;
      padding: 18px;
      margin-bottom: 18px;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    .nav {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: 16px 0 18px;
      position: sticky;
      top: 0;
      z-index: 2;
      background: rgba(238, 242, 247, .96);
      padding: 10px 0;
    }
    .nav a {
      color: #1f2937;
      text-decoration: none;
      background: white;
      border: 1px solid #d1d5db;
      border-radius: 999px;
      padding: 8px 12px;
      font-size: 14px;
    }
    .nav a:hover {
      border-color: #111827;
    }
    .section-header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 12px;
    }
    .section-header h2 {
      margin: 0 0 4px;
    }
    .section-actions {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }
    .summary-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 12px;
      margin-top: 12px;
    }
    .summary-card {
      border: 1px solid #e5e7eb;
      border-radius: 8px;
      padding: 12px;
      background: #f9fafb;
    }
    .summary-label {
      color: #6b7280;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .04em;
    }
    .summary-value {
      margin-top: 6px;
      font-size: 20px;
      font-weight: 700;
    }
    .grid-two {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 18px;
    }
    .form-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 10px;
      align-items: end;
    }
    label {
      display: flex;
      flex-direction: column;
      gap: 5px;
      color: #374151;
      font-size: 13px;
      font-weight: 700;
    }
    button {
      cursor: pointer;
      padding: 8px 12px;
      border-radius: 6px;
      border: 1px solid #9ca3af;
      background: #fff;
      color: #111827;
    }
    button.primary {
      background: #1f2937;
      color: white;
      border-color: #1f2937;
    }
    button.compact {
      padding: 6px 10px;
      font-size: 13px;
    }
    input, select {
      padding: 8px;
      border-radius: 6px;
      border: 1px solid #bbb;
      min-width: 0;
    }
    .table-wrap {
      overflow-x: auto;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 12px;
      background: white;
    }
    th, td {
      border-bottom: 1px solid #eee;
      padding: 10px 8px;
      text-align: left;
      font-size: 14px;
    }
    th {
      background: #f9fafb;
      color: #374151;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .04em;
    }
    .muted {
      color: #6b7280;
      font-size: 13px;
    }
    .badge {
      display: inline-block;
      padding: 3px 9px;
      border-radius: 999px;
      background: #e5e7eb;
      font-size: 12px;
      font-weight: 700;
    }
    .ok {
      background: #dcfce7;
    }
    .warn {
      background: #fef3c7;
    }
    .feedback {
      margin-top: 10px;
      padding: 10px 12px;
      border-radius: 8px;
      background: #f3f4f6;
      border: 1px solid #e5e7eb;
      font-size: 14px;
    }
    .feedback.success {
      background: #ecfdf5;
      border-color: #bbf7d0;
      color: #166534;
    }
    .feedback.error {
      background: #fef2f2;
      border-color: #fecaca;
      color: #991b1b;
    }
    .info-box {
      background: #f8fafc;
      border: 1px solid #e5e7eb;
      border-radius: 10px;
      padding: 12px;
      margin: 10px 0;
    }
    .secondary-text {
      color: #6b7280;
      font-size: 12px;
    }
    .market-name {
      font-weight: 700;
    }
    .future-list {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 8px;
    }
    details {
      margin-top: 12px;
    }
    summary {
      cursor: pointer;
      color: #374151;
      font-size: 14px;
      font-weight: 700;
    }
    pre {
      white-space: pre-wrap;
      background: #111827;
      color: #e5e7eb;
      padding: 12px;
      border-radius: 8px;
      overflow-x: auto;
    }
  </style>
</head>
<body>
  <div class="page">
  <div class="hero">
    <h1>Calcolo Quote - MVP</h1>
    <p>Dashboard locale per monitorare quote calcio e inviare alert Telegram sui cali quota.</p>
  </div>

  <nav class="nav" aria-label="Navigazione dashboard">
    <a href="#overview">Panoramica</a>
    <a href="#competitions">Campionati</a>
    <a href="#markets">Mercati</a>
    <a href="#automation">Automazione</a>
    <a href="#recipients">Destinatari</a>
    <a href="#recent-alerts">Alert</a>
    <a href="#notification-logs-section">Log notifiche</a>
  </nav>

  <section id="overview">
    <div class="section-header">
      <div>
        <h2>Stato operativo</h2>
        <p class="muted">Panoramica immediata di configurazione, automazione e attività recente.</p>
      </div>
      <div class="section-actions">
        <button onclick="loadStatus()">Aggiorna stato</button>
      </div>
    </div>
    <div id="dashboard-summary" class="summary-grid">
      <div class="summary-card"><div class="summary-label">Provider</div><div class="summary-value">...</div></div>
      <div class="summary-card"><div class="summary-label">Sport</div><div class="summary-value">...</div></div>
      <div class="summary-card"><div class="summary-label">Scheduler</div><div class="summary-value">...</div></div>
      <div class="summary-card"><div class="summary-label">Campionati attivi</div><div class="summary-value">...</div></div>
      <div class="summary-card"><div class="summary-label">Mercati attivi</div><div class="summary-value">...</div></div>
      <div class="summary-card"><div class="summary-label">Destinatari attivi</div><div class="summary-value">...</div></div>
      <div class="summary-card"><div class="summary-label">Alert recenti</div><div class="summary-value">...</div></div>
      <div class="summary-card"><div class="summary-label">Log notifiche</div><div class="summary-value">...</div></div>
    </div>
  </section>

  <section id="automation">
    <div class="section-header">
      <div>
        <h2>Automazione</h2>
        <p class="muted">Definisce ogni quanto controllare le quote e come evitare notifiche ripetute.</p>
      </div>
    </div>
    <div id="automation-status" class="info-box">Caricamento automazione...</div>
    <div class="form-grid">
      <label>Controllo automatico
        <select id="scheduler-enabled">
          <option value="false">Spento</option>
          <option value="true">Attivo</option>
        </select>
      </label>
      <label>Frequenza controllo
        <select id="scheduler-poll-interval-seconds">
          <option value="3">3 secondi - test locale</option>
          <option value="30">30 secondi</option>
          <option value="60">1 minuto</option>
          <option value="300">5 minuti - consigliato</option>
          <option value="900">15 minuti</option>
        </select>
      </label>
      <label>Eventi per ciclo
        <input id="scheduler-event-limit" type="number" min="1" max="10" step="1" placeholder="1">
      </label>
      <button class="primary" onclick="saveSchedulerSettings()">Salva automazione</button>
      <button onclick="loadSchedulerSettings()">Ricarica automazione</button>
    </div>
    <div id="scheduler-settings-feedback" class="feedback muted">Caricamento automazione...</div>
    <div id="scheduler-status"></div>
    <details>
      <summary>Dettagli tecnici sistema</summary>
      <pre id="system-status">Caricamento...</pre>
    </details>
  </section>

  <section id="manual-check">
    <div class="section-header">
      <div>
        <h2>Controllo quote manuale</h2>
        <p class="muted">Esegue subito un controllo quote sui campionati attivi.</p>
      </div>
      <div class="section-actions">
        <button class="primary" onclick="runManualOddsCheck()">Esegui controllo quote ora</button>
      </div>
    </div>
    <div id="manual-odds-check-feedback" class="feedback muted">Nessun controllo eseguito.</div>
    <details>
      <summary>Risposta tecnica ultimo controllo</summary>
      <pre id="manual-odds-check-result">Nessun controllo eseguito.</pre>
    </details>
  </section>

  <section id="alert-settings">
    <div class="section-header">
      <div>
        <h2>Soglie alert e cooldown</h2>
        <p class="muted">Configura le soglie. Telegram notifica solo i cali quota: Standard tra min/max, Critico oltre la soglia critica.</p>
      </div>
    </div>
    <div class="form-grid">
      <label>Min %
        <input id="alert-min-percent" type="number" step="0.01" placeholder="8">
      </label>
      <label>Max %
        <input id="alert-max-percent" type="number" step="0.01" placeholder="15">
      </label>
      <label>Critico %
        <input id="alert-critical-percent" type="number" step="0.01" placeholder="15">
      </label>
      <label>Dedup minuti
        <input id="alert-deduplication-minutes" type="number" step="1" placeholder="30">
      </label>
      <button class="primary" onclick="saveAlertSettings()">Salva soglie</button>
      <button onclick="loadAlertSettings()">Ricarica</button>
    </div>
    <div id="alert-settings-feedback" class="feedback muted">Caricamento impostazioni...</div>
    <details>
      <summary>JSON tecnico impostazioni</summary>
      <pre id="alert-settings-result">Caricamento...</pre>
    </details>
  </section>

  <section id="competitions">
    <div class="section-header">
      <div>
        <h2>Campionati da monitorare</h2>
        <p class="muted">Scegli i campionati su cui vuoi ricevere alert. Puoi aggiornare l’elenco in base agli eventi disponibili dal provider.</p>
      </div>
      <div class="section-actions">
        <button class="primary" onclick="refreshProviderCompetitions()">Aggiorna campionati dal provider</button>
        <button onclick="loadCompetitions()">Aggiorna campionati</button>
      </div>
    </div>
    <div class="info-box">
      <strong>Come usare questa sezione</strong>
      <p class="muted">Attiva solo i campionati che vuoi monitorare. I campionati non attivi restano disponibili, ma non vengono usati nel controllo quote.</p>
    </div>
    <div id="competitions-summary" class="summary-grid"></div>
    <div id="competitions-feedback" class="feedback muted">Caricamento campionati...</div>
    <div id="competitions-table"></div>
  </section>

  <section id="markets">
    <div class="section-header">
      <div>
        <h2>Mercati</h2>
        <p class="muted">Seleziona i mercati MVP supportati da monitorare.</p>
      </div>
      <div class="section-actions">
        <button onclick="loadMonitoredMarkets()">Aggiorna mercati</button>
      </div>
    </div>
    <div class="info-box">
      <strong>Mercati MVP supportati</strong>
      <p class="muted">1X2, Over/Under, Goal/No Goal e Handicap sono collegati ai mercati provider normalizzati.</p>
      <strong>Mercati futuri / da integrare</strong>
      <div class="future-list">
        <span class="badge">Doppia chance</span>
        <span class="badge">Risultato esatto</span>
        <span class="badge">Primo tempo/finale</span>
        <span class="badge">Corner</span>
        <span class="badge">Cartellini</span>
        <span class="badge">Marcatori</span>
      </div>
    </div>
    <div id="markets-feedback" class="feedback muted">Caricamento mercati...</div>
    <div id="monitored-markets"></div>
  </section>

  <section id="recipients">
    <div class="section-header">
      <div>
        <h2>Notifiche Telegram</h2>
        <p class="muted">Rileva gli account che hanno scritto al bot. Solo gli account attivati manualmente ricevono alert.</p>
      </div>
    </div>
    <div class="info-box">
      <strong>Come collegare Telegram</strong>
      <p class="muted">Apri il bot Telegram configurato per il software, premi Start o invia un messaggio, poi clicca “Rileva account Telegram”.</p>
      <p class="muted">Il codice tecnico della chat viene salvato automaticamente e non deve essere inserito manualmente.</p>
    </div>
    <div class="form-grid">
      <button class="primary" onclick="syncTelegramRecipients()">Rileva account Telegram</button>
      <button onclick="loadRecipients()">Aggiorna Telegram</button>
    </div>
    <div id="recipients-feedback" class="feedback muted">Caricamento destinatari...</div>
    <div id="recipients-table"></div>
  </section>

  <section id="recent-alerts">
    <div class="section-header">
      <div>
        <h2>Alert recenti</h2>
        <p class="muted">Storico completo degli alert. Gli aumenti restano nello storico, ma non vengono notificati via Telegram.</p>
      </div>
      <div class="section-actions">
        <select id="alerts-filter" onchange="renderAlertsTable()">
          <option value="all">Tutti</option>
          <option value="notifiable">Solo cali notificabili</option>
          <option value="increases">Aumenti non notificati</option>
          <option value="critical">Critici</option>
        </select>
        <button onclick="loadAlerts()">Aggiorna alert</button>
      </div>
    </div>
    <div id="alerts-filter-feedback" class="feedback muted">Gli alert Telegram vengono inviati solo sui cali quota.</div>
    <div id="alerts"></div>
  </section>

  <section id="notification-logs-section">
    <div class="section-header">
      <div>
        <h2>Log notifiche recenti</h2>
        <p class="muted">Esiti recenti degli invii verso destinatari configurati.</p>
      </div>
      <div class="section-actions">
        <button onclick="loadNotificationLogs()">Aggiorna log</button>
      </div>
    </div>
    <div id="notification-logs"></div>
  </section>

<script>
async function api(path, options) {
  const response = await fetch(path, options || {});
  if (!response.ok) {
    const text = await response.text();
    let message = text;
    try {
      const payload = JSON.parse(text);
      if (typeof payload.detail === "string") {
        message = payload.detail;
      } else if (payload.detail && payload.detail.message) {
        message = payload.detail.message;
      }
    } catch (error) {
      message = text;
    }
    throw new Error(response.status + " " + message);
  }
  return response.json();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

const dashboardState = {
  system: {},
  activeCompetitions: "...",
  activeMarkets: "...",
  activeRecipients: "...",
  lastManualCheck: "Nessuno"
};

function setFeedback(elementId, message, type) {
  const element = document.getElementById(elementId);
  if (!element) {
    return;
  }

  element.className = "feedback" + (type ? " " + type : " muted");
  element.textContent = message;
}

function summaryCard(label, value) {
  return `
    <div class="summary-card">
      <div class="summary-label">${escapeHtml(label)}</div>
      <div class="summary-value">${escapeHtml(value)}</div>
    </div>
  `;
}

function humanizeSeconds(seconds) {
  const value = Number(seconds || 0);
  if (value >= 3600) {
    return `${Math.round(value / 3600)} ore`;
  }
  if (value >= 60) {
    return `${Math.round(value / 60)} minuti`;
  }
  return `${value} secondi`;
}

function readableMarketName(marketName) {
  if (!marketName) {
    return "Mercato non specificato";
  }

  if (marketName === "ML") {
    return "1X2";
  }

  if (marketName.startsWith("Totals")) {
    const suffix = marketName.replace("Totals", "").trim();
    return "Over/Under" + (suffix ? ` ${suffix}` : "");
  }

  if (marketName.startsWith("Both Teams To Score")) {
    return "Goal/No Goal";
  }

  if (marketName.startsWith("Spread")) {
    const suffix = marketName.replace("Spread", "").trim();
    return "Handicap" + (suffix ? ` ${suffix}` : "");
  }

  return marketName;
}


function readableAlertType(alertType) {
  if (alertType === "critical_alert") {
    return "Critico";
  }

  if (alertType === "standard_alert") {
    return "Standard";
  }

  return alertType || "n/d";
}

function alertTypeBadgeClass(alertType) {
  return alertType === "critical_alert" ? "badge warn" : "badge ok";
}

function readableNotificationStatus(status) {
  if (status === "sent") {
    return "Inviato";
  }

  if (status === "skipped") {
    return "Non inviato";
  }

  if (status === "failed") {
    return "Errore";
  }

  return status || "n/d";
}

function notificationStatusBadgeClass(status) {
  if (status === "sent") {
    return "badge ok";
  }

  if (status === "failed") {
    return "badge warn";
  }

  return "badge";
}

function formatDateTime(value) {
  if (!value) {
    return "n/d";
  }

  return String(value).replace("T", " ").slice(0, 19);
}

function renderDashboardSummary(data) {
  if (data) {
    dashboardState.system = data;
  }

  const system = dashboardState.system || {};
  const scheduler = system.scheduler || {};
  const counts = system.database_counts || {};
  const schedulerValue = scheduler.enabled === true ? "Attivo" : "Spento";

  document.getElementById("dashboard-summary").innerHTML = [
    summaryCard("Provider", system.provider || "n/d"),
    summaryCard("Sport", system.sport || "n/d"),
    summaryCard("Scheduler status", schedulerValue),
    summaryCard("Campionati attivi", dashboardState.activeCompetitions),
    summaryCard("Mercati attivi", dashboardState.activeMarkets),
    summaryCard("Destinatari attivi", dashboardState.activeRecipients),
    summaryCard("Ultimo controllo", dashboardState.lastManualCheck),
    summaryCard("Alert recenti", counts.alerts ?? 0),
    summaryCard("Log notifiche", counts.notification_logs ?? 0)
  ].join("");
}

function renderAutomationStatus(data) {
  const scheduler = data.scheduler || {};
  const alerts = data.alerts || {};
  const schedulerEnabled = scheduler.enabled === true;
  const intervalLabel = humanizeSeconds(scheduler.poll_interval_seconds);
  const eventLimit = scheduler.event_limit ?? "n/d";
  const cooldownMinutes = alerts.deduplication_minutes ?? "n/d";

  document.getElementById("automation-status").innerHTML = `
    <div class="summary-grid">
      ${summaryCard("Controllo automatico", schedulerEnabled ? "Attivo" : "Spento")}
      ${summaryCard("Frequenza controllo", intervalLabel)}
      ${summaryCard("Eventi per ciclo", eventLimit)}
      ${summaryCard("Cooldown notifiche", `${cooldownMinutes} min`)}
    </div>
  `;

  document.getElementById("scheduler-status").innerHTML = `
    <div class="info-box">
      <strong>Come funziona</strong>
      <p class="muted">
        Il sistema confronta le nuove quote con lo storico salvato. Genera alert solo quando la variazione rientra nelle soglie configurate.
      </p>
      <p class="muted">
        Il cooldown evita notifiche ripetute per lo stesso evento, mercato, selezione e bookmaker entro ${escapeHtml(cooldownMinutes)} minuti.
      </p>
      <p class="muted">
        ${schedulerEnabled
          ? `Il controllo automatico è attivo e verifica fino a ${escapeHtml(eventLimit)} evento/i ogni ${escapeHtml(intervalLabel)}.`
          : "Il controllo automatico è spento. Puoi usare il controllo manuale oppure abilitarlo nella configurazione server e riavviare l'app."}
      </p>
    </div>
  `;
}

async function loadStatus() {
  const data = await api("/system/status");

  renderDashboardSummary(data);
  renderAutomationStatus(data);

  document.getElementById("system-status").textContent = JSON.stringify(data, null, 2);
}

async function runManualOddsCheck() {
  const resultBox = document.getElementById("manual-odds-check-result");
  setFeedback("manual-odds-check-feedback", "Controllo quote in corso...", "");
  resultBox.textContent = "Controllo in corso...";

  try {
    const data = await api("/api/odds-provider/ingest-sample?limit=1", {
      method: "POST"
    });

    resultBox.textContent = JSON.stringify(data, null, 2);
    dashboardState.lastManualCheck = "OK";
    renderDashboardSummary();
    setFeedback("manual-odds-check-feedback", "Controllo quote completato. Dashboard aggiornata.", "success");

    await loadStatus();
    await loadAlerts();
    await loadNotificationLogs();
  } catch (error) {
    resultBox.textContent = "Errore controllo quote: " + error.message;
    dashboardState.lastManualCheck = "Errore";
    renderDashboardSummary();
    setFeedback("manual-odds-check-feedback", "Controllo quote non completato. " + error.message, "error");
  }
}

async function loadAlertSettings() {
  const data = await api("/configuration/alert-settings");

  document.getElementById("alert-min-percent").value = data.min_percent;
  document.getElementById("alert-max-percent").value = data.max_percent;
  document.getElementById("alert-critical-percent").value = data.critical_percent;
  document.getElementById("alert-deduplication-minutes").value = data.deduplication_minutes;
  document.getElementById("alert-settings-result").textContent = JSON.stringify(data, null, 2);
  setFeedback("alert-settings-feedback", "Impostazioni alert caricate.", "success");
  if (dashboardState.system.alerts) {
    dashboardState.system.alerts.deduplication_minutes = data.deduplication_minutes;
    renderAutomationStatus(dashboardState.system);
  }
}

async function loadSchedulerSettings() {
  const data = await api("/configuration/scheduler-settings");

  document.getElementById("scheduler-enabled").value = String(data.enabled);
  document.getElementById("scheduler-poll-interval-seconds").value = String(data.poll_interval_seconds);
  document.getElementById("scheduler-event-limit").value = data.event_limit;
  setFeedback("scheduler-settings-feedback", "Impostazioni automazione caricate.", "success");

  await loadStatus();
}


async function saveSchedulerSettings() {
  const payload = {
    enabled: document.getElementById("scheduler-enabled").value === "true",
    poll_interval_seconds: Number(document.getElementById("scheduler-poll-interval-seconds").value),
    event_limit: Number(document.getElementById("scheduler-event-limit").value)
  };

  setFeedback("scheduler-settings-feedback", "Salvataggio automazione...", "");

  try {
    await api("/configuration/scheduler-settings", {
      method: "PUT",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload)
    });

    setFeedback("scheduler-settings-feedback", "Automazione salvata. Le nuove impostazioni vengono applicate dal prossimo ciclo scheduler.", "success");
    await loadSchedulerSettings();
  } catch (error) {
    setFeedback("scheduler-settings-feedback", "Automazione non salvata: " + error.message, "error");
  }
}


async function saveAlertSettings() {
  setFeedback("alert-settings-feedback", "Salvataggio impostazioni alert...", "");

  const payload = {
    min_percent: Number(document.getElementById("alert-min-percent").value),
    max_percent: Number(document.getElementById("alert-max-percent").value),
    critical_percent: Number(document.getElementById("alert-critical-percent").value),
    deduplication_minutes: Number(document.getElementById("alert-deduplication-minutes").value)
  };

  try {
    const data = await api("/configuration/alert-settings", {
      method: "PUT",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload)
    });

    document.getElementById("alert-settings-result").textContent = JSON.stringify(data, null, 2);
    setFeedback("alert-settings-feedback", "Impostazioni alert salvate.", "success");
    await loadStatus();
  } catch (error) {
    document.getElementById("alert-settings-result").textContent = "Errore impostazioni alert: " + error.message;
    setFeedback("alert-settings-feedback", "Impostazioni alert non salvate: " + error.message, "error");
  }
}

async function loadCompetitions() {
  const data = await api("/configuration/available-competitions");
  const activeCompetitions = data.filter((item) => item.is_active);
  const inactiveCompetitions = data.filter((item) => !item.is_active);
  const orderedCompetitions = activeCompetitions.concat(inactiveCompetitions);

  dashboardState.activeCompetitions = activeCompetitions.length;
  renderDashboardSummary();

  document.getElementById("competitions-summary").innerHTML = [
    summaryCard("Campionati attivi", activeCompetitions.length),
    summaryCard("Campionati disponibili", data.length),
    summaryCard("Non attivi", inactiveCompetitions.length)
  ].join("");

  let html = "<div class='table-wrap'><table><thead><tr><th>Campionato</th><th>Paese</th><th>Stato</th><th>Azione</th></tr></thead><tbody>";

  for (const item of orderedCompetitions) {
    const statusLabels = {
      pending: "In attesa di attivazione",
      active: "Attivo",
      disabled: "Disattivato"
    };
    const active = statusLabels[item.status] || "In attesa di attivazione";
    const badgeClass = item.status === "active" ? "badge ok" : "badge";
    const actionLabel = item.status === "active" ? "Disattiva" : "Attiva notifiche";
    const nextState = item.status === "active" ? "false" : "true";
    const nameArg = JSON.stringify(item.name || "");
    const countryArg = JSON.stringify(item.country || "");
    const slugArg = JSON.stringify(item.provider_league_slug || "");
    const providerDetail = item.provider_league_slug
      ? `<details><summary>Dettaglio provider</summary><span class="secondary-text">${escapeHtml(item.provider_league_slug)}</span></details>`
      : `<span class="secondary-text">Provider non disponibile</span>`;

    html += `<tr>
      <td>
        <strong>${escapeHtml(item.name)}</strong><br>
        ${providerDetail}
      </td>
      <td>${escapeHtml(item.country || "n/d")}</td>
      <td><span class="${badgeClass}">${active}</span></td>
      <td>
        <button class="compact ${item.is_active ? "" : "primary"}" onclick='monitorCompetition(${nameArg}, ${countryArg}, ${slugArg}, ${nextState})'>${actionLabel}</button>
      </td>
    </tr>`;
  }

  html += "</tbody></table></div>";
  document.getElementById("competitions-table").innerHTML = html;
  setFeedback("competitions-feedback", `Campionati disponibili: ${data.length}. Attivi: ${activeCompetitions.length}.`, "success");
}

async function monitorCompetition(name, country, slug, isActive) {
  setFeedback("competitions-feedback", `${isActive ? "Attivazione" : "Disattivazione"} campionato in corso...`, "");

  try {
    await api("/configuration/monitored-competitions", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        competition_name: name,
        country: country || null,
        provider: "odds_api_io",
        provider_league_slug: slug || null,
        is_active: isActive
      })
    });
    await loadCompetitions();
    setFeedback("competitions-feedback", `Campionato ${isActive ? "attivato" : "disattivato"}: ${name}.`, "success");
    await loadStatus();
  } catch (error) {
    setFeedback("competitions-feedback", "Operazione campionato non completata: " + error.message, "error");
  }
}

async function refreshProviderCompetitions() {
  setFeedback("competitions-feedback", "Aggiornamento campionati dal provider in corso...", "");

  try {
    const data = await api("/configuration/provider-competitions/refresh?limit=10", {
      method: "POST"
    });

    await loadCompetitions();
    await loadStatus();
    setFeedback(
      "competitions-feedback",
      `Campionati rilevati dagli eventi disponibili ora: ${data.competitions_found} da ${data.events_received} eventi.`,
      "success"
    );
  } catch (error) {
    setFeedback("competitions-feedback", "Aggiornamento campionati non completato. " + error.message, "error");
  }
}

async function loadMonitoredMarkets() {
  const data = await api("/configuration/monitored-markets");
  dashboardState.activeMarkets = data.filter((item) => item.is_active).length;
  renderDashboardSummary();

  let html = "<div class='table-wrap'><table><thead><tr><th>Mercato</th><th>Nome provider</th><th>Stato</th><th>Azione</th></tr></thead><tbody>";
  for (const item of data) {
    const active = item.is_active ? "Attivo" : "In attesa di attivazione";
    const badgeClass = item.is_active ? "badge ok" : "badge";
    html += `<tr>
      <td><span class="market-name">${escapeHtml(readableMarketName(item.market_name))}</span></td>
      <td><span class="secondary-text">${escapeHtml(item.market_name)}</span></td>
      <td><span class="${badgeClass}">${active}</span></td>
      <td>
        <button class="compact" onclick="toggleMonitoredMarket(${item.id}, true)">Attiva</button>
        <button class="compact" onclick="toggleMonitoredMarket(${item.id}, false)">Disattiva</button>
      </td>
    </tr>`;
  }
  html += "</tbody></table></div>";
  document.getElementById("monitored-markets").innerHTML = html;
  setFeedback("markets-feedback", `Mercati caricati: ${data.length}.`, "success");
}

async function toggleMonitoredMarket(marketId, isActive) {
  setFeedback("markets-feedback", `${isActive ? "Attivazione" : "Disattivazione"} mercato in corso...`, "");

  try {
    await api(`/configuration/monitored-markets/${marketId}/toggle?is_active=${isActive}`, {
      method: "PATCH"
    });

    await loadMonitoredMarkets();
    setFeedback("markets-feedback", `Mercato ${isActive ? "attivato" : "disattivato"}.`, "success");
    await loadStatus();
  } catch (error) {
    setFeedback("markets-feedback", "Operazione mercato non completata: " + error.message, "error");
  }
}

async function syncTelegramRecipients() {
  setFeedback("recipients-feedback", "Rilevamento account Telegram in corso...", "");

  try {
    const data = await api("/configuration/telegram-recipients/sync", {
      method: "POST"
    });

    await loadRecipients();
    await loadStatus();

    if (data.synced_count === 0) {
      setFeedback(
        "recipients-feedback",
        "Nessun account rilevato. Apri il bot Telegram, premi Start e riprova.",
        "error"
      );
      return;
    }

    setFeedback(
      "recipients-feedback",
      `Account Telegram rilevati: ${data.synced_count}. Attivali manualmente per abilitarli alle notifiche.`,
      "success"
    );
  } catch (error) {
    setFeedback("recipients-feedback", "Rilevamento Telegram non completato: " + error.message, "error");
  }
}

async function loadRecipients() {
  const data = await api("/configuration/notification-recipients");
  const telegramRecipients = data.filter((item) => item.channel === "telegram");
  const activeRecipients = telegramRecipients.filter((item) => item.status === "active");
  const pendingRecipients = telegramRecipients.filter((item) => item.status === "pending");
  const disabledRecipients = telegramRecipients.filter((item) => item.status === "disabled");
  const orderedRecipients = pendingRecipients.concat(activeRecipients, disabledRecipients);

  dashboardState.activeRecipients = activeRecipients.length;
  renderDashboardSummary();

  if (telegramRecipients.length === 0) {
    document.getElementById("recipients-table").innerHTML = "<p class='muted'>Nessun destinatario Telegram configurato.</p>";
    setFeedback("recipients-feedback", "Apri il bot Telegram, premi Start e clicca Rileva account Telegram.", "");
    return;
  }

  let html = "<div class='table-wrap'><table><thead><tr><th>Account Telegram</th><th>Stato</th><th>Azione</th></tr></thead><tbody>";
  for (const item of orderedRecipients) {
    const statusLabels = {
      pending: "In attesa di attivazione",
      active: "Attivo",
      disabled: "Disattivato"
    };
    const active = statusLabels[item.status] || "In attesa di attivazione";
    const badgeClass = item.status === "active" ? "badge ok" : "badge";
    const actionLabel = item.status === "active" ? "Disattiva" : "Attiva notifiche";
    const nextState = item.status === "active" ? "false" : "true";

    html += `<tr>
      <td><strong>${escapeHtml(item.label || "Telegram")}</strong><br><span class="secondary-text">ID tecnico salvato automaticamente</span></td>
      <td><span class="${badgeClass}">${active}</span></td>
      <td>
        <button class="compact ${item.is_active ? "" : "primary"}" onclick="toggleRecipient(${item.id}, ${nextState})">${actionLabel}</button>
      </td>
    </tr>`;
  }
  html += "</tbody></table></div>";
  document.getElementById("recipients-table").innerHTML = html;
  setFeedback("recipients-feedback", `Account Telegram: ${telegramRecipients.length}. Attivi: ${activeRecipients.length}. In attesa: ${pendingRecipients.length}. Disattivati: ${disabledRecipients.length}.`, "success");
}

async function toggleRecipient(recipientId, isActive) {
  setFeedback("recipients-feedback", `${isActive ? "Attivazione" : "Disattivazione"} destinatario Telegram in corso...`, "");

  try {
    await api(`/configuration/notification-recipients/${recipientId}/toggle?is_active=${isActive}`, {
      method: "PATCH"
    });

    await loadRecipients();
    setFeedback("recipients-feedback", `Destinatario Telegram ${isActive ? "attivato" : "disattivato"}.`, "success");
    await loadStatus();
  } catch (error) {
    setFeedback("recipients-feedback", "Operazione destinatario Telegram non completata: " + error.message, "error");
  }
}

async function loadAlerts() {
  const data = await api("/alerts?limit=20");
  dashboardState.recentAlerts = data;
  renderAlertsTable();
}


function renderAlertsTable() {
  const filterElement = document.getElementById("alerts-filter");
  const filter = filterElement ? filterElement.value : "all";
  const data = dashboardState.recentAlerts || [];

  let filtered = data;
  if (filter === "notifiable") {
    filtered = data.filter((item) => item.direction === "decrease");
  } else if (filter === "increases") {
    filtered = data.filter((item) => item.direction === "increase");
  } else if (filter === "critical") {
    filtered = data.filter((item) => item.alert_type === "critical_alert");
  }

  if (filtered.length === 0) {
    document.getElementById("alerts").innerHTML = "<p class='muted'>Nessun alert per il filtro selezionato.</p>";
    setFeedback("alerts-filter-feedback", `Filtro applicato: ${filtered.length} alert visualizzati su ${data.length}.`, "");
    return;
  }

  let html = "<div class='table-wrap'><table><thead><tr><th>Evento</th><th>Bookmaker</th><th>Mercato</th><th>Selezione</th><th>Variazione</th><th>Notifica</th><th>Tipo</th><th>Data</th></tr></thead><tbody>";
  for (const item of filtered) {
    const variation = `${item.variation_percent}%`;
    const alertLabel = readableAlertType(item.alert_type);
    const alertBadgeClass = alertTypeBadgeClass(item.alert_type);
    const notificationLabel = item.direction === "decrease" ? "Telegram" : "Solo storico";
    const notificationBadgeClass = item.direction === "decrease" ? "badge ok" : "badge";

    html += `<tr>
      <td><strong>${escapeHtml(item.event)}</strong></td>
      <td>${escapeHtml(item.bookmaker)}</td>
      <td>${escapeHtml(readableMarketName(item.market))}</td>
      <td>${escapeHtml(item.selection)}</td>
      <td><strong>${escapeHtml(variation)}</strong></td>
      <td><span class="${notificationBadgeClass}">${escapeHtml(notificationLabel)}</span></td>
      <td><span class="${alertBadgeClass}">${escapeHtml(alertLabel)}</span></td>
      <td><span class="secondary-text">${escapeHtml(formatDateTime(item.created_at))}</span></td>
    </tr>`;
  }
  html += "</tbody></table></div>";
  document.getElementById("alerts").innerHTML = html;
  setFeedback("alerts-filter-feedback", `Filtro applicato: ${filtered.length} alert visualizzati su ${data.length}.`, "success");
}

async function loadNotificationLogs() {
  const data = await api("/notification-logs?limit=20");
  if (data.length === 0) {
    document.getElementById("notification-logs").innerHTML = "<p class='muted'>Nessun log notifica recente.</p>";
    return;
  }

  let html = "<div class='table-wrap'><table><thead><tr><th>Canale</th><th>Stato</th><th>Destinatario</th><th>Dettaglio</th><th>Data</th></tr></thead><tbody>";
  for (const item of data) {
    const statusLabel = readableNotificationStatus(item.status);
    const statusBadgeClass = notificationStatusBadgeClass(item.status);
    const errorDetail = item.error_message ? item.error_message : "Nessun errore";

    html += `<tr>
      <td>Telegram</td>
      <td><span class="${statusBadgeClass}">${escapeHtml(statusLabel)}</span></td>
      <td>${escapeHtml(item.recipient || "n/d")}</td>
      <td><span class="secondary-text">${escapeHtml(errorDetail)}</span></td>
      <td><span class="secondary-text">${escapeHtml(formatDateTime(item.sent_at))}</span></td>
    </tr>`;
  }
  html += "</tbody></table></div>";
  document.getElementById("notification-logs").innerHTML = html;
}

loadStatus();
loadAlertSettings();
loadSchedulerSettings();
loadCompetitions();
loadMonitoredMarkets();
loadRecipients();
loadAlerts();
loadNotificationLogs();
</script>
  </div>
</body>
</html>
"""
