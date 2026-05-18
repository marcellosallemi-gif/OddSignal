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
      margin: 24px;
      background: #f6f7f9;
      color: #1f2937;
    }
    h1, h2 {
      margin-bottom: 8px;
    }
    section {
      background: white;
      border: 1px solid #ddd;
      border-radius: 10px;
      padding: 16px;
      margin-bottom: 18px;
    }
    button {
      cursor: pointer;
      padding: 8px 12px;
      border-radius: 6px;
      border: 1px solid #888;
      background: #fff;
    }
    button.primary {
      background: #1f2937;
      color: white;
      border-color: #1f2937;
    }
    input, select {
      padding: 8px;
      margin: 4px;
      border-radius: 6px;
      border: 1px solid #bbb;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 12px;
    }
    th, td {
      border-bottom: 1px solid #eee;
      padding: 8px;
      text-align: left;
      font-size: 14px;
    }
    th {
      background: #f0f2f5;
    }
    .muted {
      color: #6b7280;
      font-size: 13px;
    }
    .badge {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 999px;
      background: #e5e7eb;
      font-size: 12px;
    }
    .ok {
      background: #dcfce7;
    }
    .warn {
      background: #fef3c7;
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
  <h1>Calcolo Quote - MVP</h1>
  <p class="muted">Interfaccia minima per configurare campionati, destinatari e controllare alert.</p>

  <section>
    <h2>Stato sistema</h2>
    <button onclick="loadStatus()">Aggiorna stato</button>
    <div id="scheduler-status"></div>
    <pre id="system-status">Caricamento...</pre>
  </section>

  <section>
    <h2>Controllo quote manuale</h2>
    <p class="muted">Esegue subito un controllo quote sui campionati attivi. Utile per testare senza terminale.</p>
    <button class="primary" onclick="runManualOddsCheck()">Esegui controllo quote ora</button>
    <pre id="manual-odds-check-result">Nessun controllo eseguito.</pre>
  </section>

  <section>
    <h2>Impostazioni alert</h2>
    <p class="muted">Configura le soglie senza modificare il file .env.</p>
    <input id="alert-min-percent" type="number" step="0.01" placeholder="Min %">
    <input id="alert-max-percent" type="number" step="0.01" placeholder="Max %">
    <input id="alert-critical-percent" type="number" step="0.01" placeholder="Critico %">
    <input id="alert-deduplication-minutes" type="number" step="1" placeholder="Dedup minuti">
    <button class="primary" onclick="saveAlertSettings()">Salva impostazioni alert</button>
    <button onclick="loadAlertSettings()">Ricarica impostazioni</button>
    <pre id="alert-settings-result">Caricamento...</pre>
  </section>

  <section>
    <h2>Campionati disponibili</h2>
    <p class="muted">Attiva solo i campionati per cui vuoi ricevere alert.</p>
    <button onclick="loadCompetitions()">Aggiorna campionati</button>
    <div id="competitions"></div>
  </section>

  <section>
    <h2>Destinatari notifiche</h2>
    <p class="muted">Telegram usa il chat_id. Il telefono viene salvato per integrazioni future SMS/WhatsApp ufficiali.</p>
    <select id="recipient-channel">
      <option value="telegram">telegram</option>
      <option value="phone">phone</option>
    </select>
    <input id="recipient-value" placeholder="chat_id Telegram o numero telefono">
    <input id="recipient-label" placeholder="etichetta">
    <button class="primary" onclick="saveRecipient()">Salva destinatario</button>
    <button onclick="loadRecipients()">Aggiorna destinatari</button>
    <div id="recipients"></div>
  </section>

  <section>
    <h2>Alert</h2>
    <button onclick="loadAlerts()">Aggiorna alert</button>
    <div id="alerts"></div>
  </section>

  <section>
    <h2>Log notifiche</h2>
    <button onclick="loadNotificationLogs()">Aggiorna log</button>
    <div id="notification-logs"></div>
  </section>

<script>
async function api(path, options) {
  const response = await fetch(path, options || {});
  if (!response.ok) {
    const text = await response.text();
    throw new Error(response.status + " " + text);
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

async function loadStatus() {
  const data = await api("/system/status");

  const scheduler = data.scheduler || {};
  const schedulerEnabled = scheduler.enabled === true;
  const schedulerHtml = `
    <p>
      <strong>Scheduler automatico:</strong>
      <span class="${schedulerEnabled ? "badge ok" : "badge warn"}">
        ${schedulerEnabled ? "Attivo" : "Spento"}
      </span>
    </p>
    <p class="muted">
      Intervallo polling: ${escapeHtml(scheduler.poll_interval_seconds)} secondi |
      Eventi per ciclo: ${escapeHtml(scheduler.event_limit)}
    </p>
    <p class="muted">
      ${schedulerEnabled
        ? "Il sistema può eseguire controlli automatici secondo la configurazione."
        : "Lo scheduler è spento: usa il controllo quote manuale oppure abilitalo da .env e riavvia il server."}
    </p>
  `;

  document.getElementById("scheduler-status").innerHTML = schedulerHtml;
  document.getElementById("system-status").textContent = JSON.stringify(data, null, 2);
}

async function runManualOddsCheck() {
  const resultBox = document.getElementById("manual-odds-check-result");
  resultBox.textContent = "Controllo in corso...";

  try {
    const data = await api("/api/odds-provider/ingest-sample?limit=1", {
      method: "POST"
    });

    resultBox.textContent = JSON.stringify(data, null, 2);

    await loadStatus();
    await loadAlerts();
    await loadNotificationLogs();
  } catch (error) {
    resultBox.textContent = "Errore controllo quote: " + error.message;
  }
}

async function loadAlertSettings() {
  const data = await api("/configuration/alert-settings");

  document.getElementById("alert-min-percent").value = data.min_percent;
  document.getElementById("alert-max-percent").value = data.max_percent;
  document.getElementById("alert-critical-percent").value = data.critical_percent;
  document.getElementById("alert-deduplication-minutes").value = data.deduplication_minutes;
  document.getElementById("alert-settings-result").textContent = JSON.stringify(data, null, 2);
}

async function saveAlertSettings() {
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
    await loadStatus();
  } catch (error) {
    document.getElementById("alert-settings-result").textContent = "Errore impostazioni alert: " + error.message;
  }
}

async function loadCompetitions() {
  const data = await api("/configuration/available-competitions");
  let html = "<table><thead><tr><th>Campionato</th><th>Paese</th><th>Slug provider</th><th>Stato</th><th>Azione</th></tr></thead><tbody>";
  for (const item of data) {
    const active = item.is_active ? "Attivo" : "Non attivo";
    const badgeClass = item.is_active ? "badge ok" : "badge";
    html += `<tr>
      <td>${escapeHtml(item.name)}</td>
      <td>${escapeHtml(item.country)}</td>
      <td>${escapeHtml(item.provider_league_slug)}</td>
      <td><span class="${badgeClass}">${active}</span></td>
      <td>
        <button onclick="monitorCompetition('${escapeHtml(item.name)}','${escapeHtml(item.country)}','${escapeHtml(item.provider_league_slug)}', true)">Attiva</button>
        <button onclick="monitorCompetition('${escapeHtml(item.name)}','${escapeHtml(item.country)}','${escapeHtml(item.provider_league_slug)}', false)">Disattiva</button>
      </td>
    </tr>`;
  }
  html += "</tbody></table>";
  document.getElementById("competitions").innerHTML = html;
}

async function monitorCompetition(name, country, slug, isActive) {
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
  await loadStatus();
}

async function saveRecipient() {
  const channel = document.getElementById("recipient-channel").value;
  const value = document.getElementById("recipient-value").value.trim();
  const label = document.getElementById("recipient-label").value.trim();

  if (!value) {
    alert("Inserisci un destinatario.");
    return;
  }

  await api("/configuration/notification-recipients", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      channel: channel,
      recipient_value: value,
      label: label || null,
      is_active: true
    })
  });

  document.getElementById("recipient-value").value = "";
  document.getElementById("recipient-label").value = "";
  await loadRecipients();
}

async function loadRecipients() {
  const data = await api("/configuration/notification-recipients");
  let html = "<table><thead><tr><th>Canale</th><th>Destinatario</th><th>Etichetta</th><th>Stato</th><th>Azione</th></tr></thead><tbody>";
  for (const item of data) {
    const active = item.is_active ? "Attivo" : "Non attivo";
    const badgeClass = item.is_active ? "badge ok" : "badge";
    html += `<tr>
      <td>${escapeHtml(item.channel)}</td>
      <td>${escapeHtml(item.recipient_value)}</td>
      <td>${escapeHtml(item.label)}</td>
      <td><span class="${badgeClass}">${active}</span></td>
      <td>
        <button onclick="toggleRecipient(${item.id}, true)">Attiva</button>
        <button onclick="toggleRecipient(${item.id}, false)">Disattiva</button>
      </td>
    </tr>`;
  }
  html += "</tbody></table>";
  document.getElementById("recipients").innerHTML = html;
}

async function toggleRecipient(recipientId, isActive) {
  await api(`/configuration/notification-recipients/${recipientId}/toggle?is_active=${isActive}`, {
    method: "PATCH"
  });

  await loadRecipients();
  await loadStatus();
}

async function loadAlerts() {
  const data = await api("/alerts?limit=20");
  let html = "<table><thead><tr><th>Evento</th><th>Bookmaker</th><th>Mercato</th><th>Selezione</th><th>Var.</th><th>Tipo</th></tr></thead><tbody>";
  for (const item of data) {
    html += `<tr>
      <td>${escapeHtml(item.event)}</td>
      <td>${escapeHtml(item.bookmaker)}</td>
      <td>${escapeHtml(item.market)}</td>
      <td>${escapeHtml(item.selection)}</td>
      <td>${escapeHtml(item.variation_percent)}%</td>
      <td>${escapeHtml(item.alert_type)}</td>
    </tr>`;
  }
  html += "</tbody></table>";
  document.getElementById("alerts").innerHTML = html;
}

async function loadNotificationLogs() {
  const data = await api("/notification-logs?limit=20");
  let html = "<table><thead><tr><th>Canale</th><th>Stato</th><th>Destinatario</th><th>Errore</th><th>Data</th></tr></thead><tbody>";
  for (const item of data) {
    html += `<tr>
      <td>${escapeHtml(item.channel)}</td>
      <td>${escapeHtml(item.status)}</td>
      <td>${escapeHtml(item.recipient)}</td>
      <td>${escapeHtml(item.error_message)}</td>
      <td>${escapeHtml(item.sent_at)}</td>
    </tr>`;
  }
  html += "</tbody></table>";
  document.getElementById("notification-logs").innerHTML = html;
}

loadStatus();
loadAlertSettings();
loadCompetitions();
loadRecipients();
loadAlerts();
loadNotificationLogs();
</script>
</body>
</html>
"""
