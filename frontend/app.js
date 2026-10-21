/**
 * Samsung Smart TV Controller - Web & Native Client
 * High-performance remote interface with tactile keyboard, audio feedback & macOS tooltips
 */

document.addEventListener("DOMContentLoaded", () => {
  // Check if running inside native macOS AppKit app
  function isNativeApp() {
    return !!(window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.samsung);
  }

  // Elements
  const statusDot = document.getElementById("statusDot");
  const tvNameEl = document.getElementById("tvName");
  const tvSubEl = document.getElementById("tvSub");
  const toastEl = document.getElementById("toast");
  const btnPower = document.getElementById("btnPower");
  const btnToggleSound = document.getElementById("btnToggleSound");
  const modalBackdrop = document.getElementById("modalBackdrop");
  const tooltipEl = document.getElementById("tooltip");

  // Drawers
  const keypadDrawer = document.getElementById("keypadDrawer");
  const textDrawer = document.getElementById("textDrawer");
  const settingsDrawer = document.getElementById("settingsDrawer");
  const btnToggleKeypad = document.getElementById("btnToggleKeypad");
  const btnToggleKeyboard = document.getElementById("btnToggleKeyboard");
  const btnOpenSettings = document.getElementById("btnOpenSettings");
  const closeKeypad = document.getElementById("closeKeypad");
  const closeText = document.getElementById("closeText");
  const closeSettings = document.getElementById("closeSettings");
  const btnDoneKeypad = document.getElementById("btnDoneKeypad");
  const btnDoneText = document.getElementById("btnDoneText");
  const btnDoneSettings = document.getElementById("btnDoneSettings");

  // Forms
  const tvTextInput = document.getElementById("tvTextInput");
  const btnSendText = document.getElementById("btnSendText");
  const tvUrlInput = document.getElementById("tvUrlInput");
  const btnOpenUrl = document.getElementById("btnOpenUrl");
  const settingIp = document.getElementById("settingIp");
  const settingMac = document.getElementById("settingMac");
  const settingPort = document.getElementById("settingPort");
  const btnSaveSettings = document.getElementById("btnSaveSettings");
  const btnRunDiscovery = document.getElementById("btnRunDiscovery");
  const discoveryResults = document.getElementById("discoveryResults");

  // Sound State
  let soundEnabled = true;
  let audioCtx = null;

  function initAudio() {
    if (!audioCtx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) {
        audioCtx = new AudioCtx();
      }
    }
  }

  function playClickSound() {
    if (!soundEnabled) return;
    try {
      initAudio();
      if (!audioCtx) return;
      if (audioCtx.state === "suspended") {
        audioCtx.resume();
      }
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(800, audioCtx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(200, audioCtx.currentTime + 0.03);
      gain.gain.setValueAtTime(0.08, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.03);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.03);
    } catch (e) {
      // Audio autoplay policy
    }
  }

  // Toast System
  let toastTimer = null;
  function showToast(message, duration = 2000) {
    if (toastTimer) clearTimeout(toastTimer);
    toastEl.textContent = message;
    toastEl.classList.add("show");
    toastTimer = setTimeout(() => {
      toastEl.classList.remove("show");
    }, duration);
  }

  // =========================================================================
  // Floating Tooltip Engine
  // =========================================================================
  let tooltipTimeout = null;

  function showTooltip(el) {
    const title = el.getAttribute("data-tooltip-title");
    if (!title) return;

    const desc = el.getAttribute("data-tooltip-desc") || "";
    const key = el.getAttribute("data-tooltip-key") || "";

    let html = `<span class="tooltip-title">${title}</span>`;
    if (desc) {
      html += `<span class="tooltip-desc">${desc}</span>`;
    }
    if (key) {
      html += `<span class="tooltip-badge">${key}</span>`;
    }

    tooltipEl.innerHTML = html;
    tooltipEl.classList.add("visible");

    const rect = el.getBoundingClientRect();
    const tipRect = tooltipEl.getBoundingClientRect();

    let top = rect.top - tipRect.height - 8;
    if (top < 10) {
      top = rect.bottom + 8;
    }

    let left = rect.left + (rect.width / 2) - (tipRect.width / 2);
    if (left < 10) left = 10;
    if (left + tipRect.width > window.innerWidth - 10) {
      left = window.innerWidth - tipRect.width - 10;
    }

    tooltipEl.style.top = `${top}px`;
    tooltipEl.style.left = `${left}px`;
  }

  function hideTooltip() {
    tooltipEl.classList.remove("visible");
  }

  document.querySelectorAll("[data-tooltip-title]").forEach(el => {
    el.addEventListener("mouseenter", () => {
      clearTimeout(tooltipTimeout);
      showTooltip(el);
    });
    el.addEventListener("mouseleave", hideTooltip);
    el.addEventListener("click", hideTooltip);
  });

  // =========================================================================
  // Command Dispatch (Native Swift vs REST API)
  // =========================================================================
  async function sendKey(key) {
    playClickSound();
    if (isNativeApp()) {
      window.webkit.messageHandlers.samsung.postMessage({ action: "key", key });
      return;
    }
    try {
      const res = await fetch("/api/key", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key })
      });
      const data = await res.json();
      if (!res.ok) {
        showToast(`❌ ${data.detail || "Key failed"}`);
      }
    } catch (err) {
      showToast(`❌ Network error: ${err.message}`);
    }
  }

  async function sendPowerAction(action = "toggle") {
    playClickSound();
    showToast(`⚡ Power ${action}...`);
    if (isNativeApp()) {
      window.webkit.messageHandlers.samsung.postMessage({ action: "power", actionType: action });
      return;
    }
    try {
      const res = await fetch("/api/power", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action })
      });
      const data = await res.json();
      showToast(data.success ? `✅ ${data.message}` : `❌ ${data.message}`);
      pollStatus();
    } catch (err) {
      showToast(`❌ Power failed: ${err.message}`);
    }
  }

  async function launchApp(appId, appName) {
    playClickSound();
    showToast(`🚀 Launching ${appName}...`);
    // Reset/start playback session tracking for the launched streaming service
    sessionSeconds = 0;
    startSessionTimer();

    if (isNativeApp()) {
      window.webkit.messageHandlers.samsung.postMessage({ action: "app", appId });
      return;
    }
    try {
      const res = await fetch("/api/app", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ app_id: appId })
      });
      const data = await res.json();
      showToast(data.success ? `✅ Launched ${appName}` : `❌ Failed to launch`);
    } catch (err) {
      showToast(`❌ Launch error: ${err.message}`);
    }
  }

  // =========================================================================
  // Universal Video Playback & Seek Bar Engine (All Streaming Services)
  // =========================================================================
  const seekSlider = document.getElementById("seekSlider");
  const seekTimeCurrent = document.getElementById("seekTimeCurrent");
  const seekTimeTotal = document.getElementById("seekTimeTotal");
  const seekDeltaBadge = document.getElementById("seekDeltaBadge");
  const btnPlayPause = document.getElementById("btnPlayPause");

  let isPlaying = false;
  let sessionSeconds = 0;
  let sessionTimer = null;
  let isDraggingSlider = false;
  let lastSliderVal = 0;
  let upnpActive = false;
  let upnpDurationSec = 0;

  function formatTime(totalSec) {
    const s = Math.max(0, Math.floor(totalSec));
    const hrs = Math.floor(s / 3600);
    const mins = Math.floor((s % 3600) / 60);
    const secs = s % 60;
    if (hrs > 0) {
      return `${hrs}:${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
    }
    return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  }

  function updateSliderUI() {
    if (upnpActive && upnpDurationSec > 0) {
      seekSlider.max = upnpDurationSec;
      seekSlider.value = sessionSeconds;
      seekTimeCurrent.textContent = formatTime(sessionSeconds);
      seekTimeTotal.textContent = formatTime(upnpDurationSec);
    } else {
      // Universal Virtual Scrubber Mode (for Prime, Netflix, YouTube, Hotstar)
      seekSlider.max = 3600;
      seekSlider.value = sessionSeconds % 3600;
      seekTimeCurrent.textContent = formatTime(sessionSeconds);
      seekTimeTotal.textContent = isPlaying ? "PLAYING" : "SCRUB";
    }
  }

  function adjustSessionTimer(deltaSec) {
    if (!isPlaying) {
      startSessionTimer();
    }
    sessionSeconds = Math.max(0, sessionSeconds + deltaSec);
    updateSliderUI();
  }

  function startSessionTimer() {
    isPlaying = true;
    if (sessionTimer) clearInterval(sessionTimer);
    sessionTimer = setInterval(() => {
      if (!isDraggingSlider) {
        sessionSeconds += 1;
        updateSliderUI();
      }
    }, 1000);
  }

  function pauseSessionTimer() {
    isPlaying = false;
    if (sessionTimer) {
      clearInterval(sessionTimer);
      sessionTimer = null;
    }
  }

  async function sendSeek(seconds, targetTime = null) {
    playClickSound();
    const direction = seconds > 0 ? "⏩ +" : "⏪ ";
    const displaySec = `${direction}${Math.abs(seconds)}s`;
    showToast(`🎬 Seeking ${displaySec}...`);

    try {
      const payload = { seconds };
      if (targetTime) payload.target_time = targetTime;

      const res = await fetch("/api/seek", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (res.ok) {
        showToast(`✅ ${data.message || displaySec}`);
        adjustSessionTimer(seconds);
      } else {
        showToast(`❌ ${data.detail || "Seek failed"}`);
      }
    } catch (err) {
      showToast(`❌ Seek error: ${err.message}`);
    }
  }

  // Play/Pause button toggles session timer
  if (btnPlayPause) {
    btnPlayPause.addEventListener("click", () => {
      if (isPlaying) {
        pauseSessionTimer();
      } else {
        startSessionTimer();
      }
    });
  }

  // Slider Dragging / Scrubbing
  if (seekSlider) {
    seekSlider.addEventListener("mousedown", () => {
      isDraggingSlider = true;
      lastSliderVal = parseInt(seekSlider.value, 10);
    });

    seekSlider.addEventListener("touchstart", () => {
      isDraggingSlider = true;
      lastSliderVal = parseInt(seekSlider.value, 10);
    });

    seekSlider.addEventListener("input", () => {
      const currentVal = parseInt(seekSlider.value, 10);
      const delta = currentVal - lastSliderVal;
      
      const maxVal = parseInt(seekSlider.max, 10) || 100;
      const percent = maxVal > 0 ? currentVal / maxVal : 0;
      if (seekDeltaBadge) {
        seekDeltaBadge.style.left = `${percent * 100}%`;
        const sign = delta >= 0 ? "+" : "-";
        seekDeltaBadge.textContent = `${sign}${formatTime(Math.abs(delta))}`;
        seekDeltaBadge.classList.add("show");
      }
      seekTimeCurrent.textContent = formatTime(currentVal);
    });

    seekSlider.addEventListener("change", () => {
      isDraggingSlider = false;
      if (seekDeltaBadge) seekDeltaBadge.classList.remove("show");
      const currentVal = parseInt(seekSlider.value, 10);
      const delta = currentVal - lastSliderVal;

      if (upnpActive && upnpDurationSec > 0) {
        const targetStr = formatTime(currentVal);
        sendSeek(delta, targetStr);
      } else {
        let seekDelta = Math.round(delta / 10) * 10;
        if (seekDelta === 0 && delta !== 0) {
          seekDelta = delta > 0 ? 10 : -10;
        }
        if (seekDelta !== 0) {
          sendSeek(seekDelta);
        }
      }
      lastSliderVal = currentVal;
      sessionSeconds = currentVal;
    });

    seekSlider.addEventListener("mouseup", () => {
      isDraggingSlider = false;
      if (seekDeltaBadge) seekDeltaBadge.classList.remove("show");
    });

    seekSlider.addEventListener("touchend", () => {
      isDraggingSlider = false;
      if (seekDeltaBadge) seekDeltaBadge.classList.remove("show");
    });
  }

  // Quick Seek Step Buttons
  document.querySelectorAll(".seek-step-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const sec = parseInt(btn.getAttribute("data-seek"), 10);
      if (sec) {
        btn.classList.add("is-active");
        setTimeout(() => btn.classList.remove("is-active"), 200);
        sendSeek(sec);
      }
    });
  });

  async function pollMediaStatus() {
    try {
      const res = await fetch("/api/media/status");
      if (res.ok) {
        const data = await res.json();
        if (data && data.active && data.duration_sec > 0) {
          upnpActive = true;
          upnpDurationSec = data.duration_sec;
          if (!isDraggingSlider) {
            sessionSeconds = data.position_sec;
            updateSliderUI();
          }
        } else {
          upnpActive = false;
        }
      }
    } catch (e) {}
  }

  async function openUrl(url) {
    playClickSound();
    showToast(`🌐 Opening URL on TV...`);
    if (isNativeApp()) {
      window.webkit.messageHandlers.samsung.postMessage({ action: "browser", url });
      closeAllDrawers();
      return;
    }
    try {
      const res = await fetch("/api/browser", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url })
      });
      const data = await res.json();
      showToast(data.success ? `✅ Opened in TV Browser` : `❌ ${data.detail}`);
      closeAllDrawers();
    } catch (err) {
      showToast(`❌ Error: ${err.message}`);
    }
  }

  async function sendText(text) {
    playClickSound();
    if (!text.trim()) return;
    if (isNativeApp()) {
      window.webkit.messageHandlers.samsung.postMessage({ action: "text", text });
      showToast(`✅ Sent "${text}"`);
      tvTextInput.value = "";
      closeAllDrawers();
      return;
    }
    try {
      const res = await fetch("/api/text", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text })
      });
      const data = await res.json();
      showToast(data.success ? `✅ Sent "${text}"` : `❌ ${data.detail}`);
      tvTextInput.value = "";
      closeAllDrawers();
    } catch (err) {
      showToast(`❌ Error: ${err.message}`);
    }
  }

  // =========================================================================
  // Status Polling & Callbacks
  // =========================================================================
  async function pollStatus() {
    if (isNativeApp()) {
      window.webkit.messageHandlers.samsung.postMessage({ action: "getStatus" });
      return;
    }
    try {
      const res = await fetch("/api/status");
      if (res.ok) {
        const info = await res.json();
        updateStatusView(info);
        if (info.online) {
          pollMediaStatus();
        }
      }
    } catch (e) {
      statusDot.className = "status-dot offline";
      tvSubEl.textContent = "Server Offline";
    }
  }

  function updateStatusView(info) {
    tvNameEl.textContent = info.name || "Samsung Smart TV";
    tvSubEl.textContent = `${info.model || ""} • ${info.ip || ""}`;
    
    statusDot.className = "status-dot";
    if (info.online) {
      statusDot.classList.add("online");
    } else if (info.power_state === "standby") {
      statusDot.classList.add("standby");
    } else {
      statusDot.classList.add("offline");
    }
  }

  // Exposed for Native macOS App callbacks
  window.updateStatusFromNative = function(info) {
    updateStatusView(info);
  };

  window.updateConfigFromNative = function(cfg) {
    settingIp.value = cfg.ip || "";
    settingMac.value = cfg.mac || "";
    settingPort.value = cfg.port || 8002;
  };

  window.updateDiscoveryFromNative = function(tvs) {
    renderDiscoveryResults(tvs);
  };

  // =========================================================================
  // Drawers & Popup Management
  // =========================================================================
  function isAnyDrawerOpen() {
    return keypadDrawer.classList.contains("open") ||
           textDrawer.classList.contains("open") ||
           settingsDrawer.classList.contains("open");
  }

  function closeAllDrawers() {
    keypadDrawer.classList.remove("open");
    textDrawer.classList.remove("open");
    settingsDrawer.classList.remove("open");
    modalBackdrop.classList.remove("show");
  }

  function openDrawer(drawer) {
    closeAllDrawers();
    drawer.classList.add("open");
    modalBackdrop.classList.add("show");
  }

  btnToggleKeypad.addEventListener("click", () => {
    if (keypadDrawer.classList.contains("open")) {
      closeAllDrawers();
    } else {
      openDrawer(keypadDrawer);
    }
  });

  btnToggleKeyboard.addEventListener("click", () => {
    if (textDrawer.classList.contains("open")) {
      closeAllDrawers();
    } else {
      openDrawer(textDrawer);
      setTimeout(() => tvTextInput.focus(), 250);
    }
  });

  btnOpenSettings.addEventListener("click", async () => {
    if (settingsDrawer.classList.contains("open")) {
      closeAllDrawers();
    } else {
      openDrawer(settingsDrawer);
      if (isNativeApp()) {
        window.webkit.messageHandlers.samsung.postMessage({ action: "getConfig" });
      } else {
        try {
          const res = await fetch("/api/config");
          if (res.ok) {
            const cfg = await res.json();
            settingIp.value = cfg.ip || "";
            settingMac.value = cfg.mac || "";
            settingPort.value = cfg.port || 8002;
          }
        } catch (e) {}
      }
    }
  });

  modalBackdrop.addEventListener("click", closeAllDrawers);
  closeKeypad.addEventListener("click", closeAllDrawers);
  closeText.addEventListener("click", closeAllDrawers);
  closeSettings.addEventListener("click", closeAllDrawers);
  if (btnDoneKeypad) btnDoneKeypad.addEventListener("click", closeAllDrawers);
  if (btnDoneText) btnDoneText.addEventListener("click", closeAllDrawers);
  if (btnDoneSettings) btnDoneSettings.addEventListener("click", closeAllDrawers);

  // Settings Save & LAN Discovery
  btnSaveSettings.addEventListener("click", async () => {
    playClickSound();
    const payload = {
      ip: settingIp.value.trim(),
      mac: settingMac.value.trim(),
      port: parseInt(settingPort.value, 10) || 8002
    };

    if (isNativeApp()) {
      window.webkit.messageHandlers.samsung.postMessage({ action: "saveConfig", ...payload });
      showToast("✅ Settings saved!");
      closeAllDrawers();
      return;
    }

    try {
      const res = await fetch("/api/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        showToast("✅ Settings saved!");
        closeAllDrawers();
        pollStatus();
      }
    } catch (err) {
      showToast(`❌ Failed to save: ${err.message}`);
    }
  });

  btnRunDiscovery.addEventListener("click", async () => {
    playClickSound();
    discoveryResults.innerHTML = '<div style="color: #8b8f9e; font-size: 11px; padding: 8px;">Scanning LAN (SSDP)...</div>';

    if (isNativeApp()) {
      window.webkit.messageHandlers.samsung.postMessage({ action: "discover" });
      return;
    }

    try {
      const res = await fetch("/api/discover", { method: "POST" });
      const data = await res.json();
      renderDiscoveryResults(data.discovered || []);
    } catch (err) {
      discoveryResults.innerHTML = `<div style="color: #ff453a; font-size: 11px;">Scan failed: ${err.message}</div>`;
    }
  });

  function renderDiscoveryResults(tvs) {
    if (!tvs || tvs.length === 0) {
      discoveryResults.innerHTML = '<div style="color: #ff453a; font-size: 11px; padding: 8px;">No Samsung TVs found.</div>';
      return;
    }
    discoveryResults.innerHTML = "";
    tvs.forEach(tv => {
      const item = document.createElement("div");
      item.className = "discovered-item";
      item.innerHTML = `
        <div>
          <strong>${tv.name || tv.ip}</strong><br>
          <span style="color: #8b8f9e;">${tv.ip} ${tv.mac ? '• ' + tv.mac : ''}</span>
        </div>
        <button class="action-btn" style="padding: 4px 10px; font-size: 11px;">Select</button>
      `;
      item.querySelector("button").addEventListener("click", async () => {
        playClickSound();
        settingIp.value = tv.ip;
        if (tv.mac) settingMac.value = tv.mac;

        if (isNativeApp()) {
          window.webkit.messageHandlers.samsung.postMessage({ action: "saveConfig", ip: tv.ip, mac: tv.mac || "" });
          showToast(`✅ Connected to ${tv.name || tv.ip}`);
          closeAllDrawers();
          return;
        }

        try {
          await fetch("/api/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ip: tv.ip, mac: tv.mac || "" })
          });
          showToast(`✅ Connected to ${tv.name || tv.ip}`);
          closeAllDrawers();
          pollStatus();
        } catch (e) {
          showToast(`Selected ${tv.ip}`);
        }
      });
      discoveryResults.appendChild(item);
    });
  }

  // Sound Toggle
  btnToggleSound.addEventListener("click", () => {
    soundEnabled = !soundEnabled;
    btnToggleSound.classList.toggle("muted", !soundEnabled);
    showToast(soundEnabled ? "🔊 Click sound on" : "🔇 Click sound off");
  });

  // Buttons with [data-key]
  document.querySelectorAll("[data-key]").forEach(btn => {
    btn.addEventListener("click", () => {
      const key = btn.getAttribute("data-key");
      if (key) sendKey(key);
    });
  });

  // Power Button
  btnPower.addEventListener("click", () => sendPowerAction("toggle"));

  // App Cards
  document.querySelectorAll(".app-card").forEach(card => {
    card.addEventListener("click", () => {
      const appId = card.getAttribute("data-app-id");
      const appName = card.querySelector(".app-name").textContent;
      if (appId) launchApp(appId, appName);
    });
  });

  // Text Form & URL Form
  btnSendText.addEventListener("click", () => sendText(tvTextInput.value));
  tvTextInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendText(tvTextInput.value);
  });

  btnOpenUrl.addEventListener("click", () => openUrl(tvUrlInput.value));
  tvUrlInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") openUrl(tvUrlInput.value);
  });

  // =========================================================================
  // Physical Mac Keyboard Shortcuts Integration
  // =========================================================================
  window.addEventListener("keydown", (e) => {
    if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") {
      if (e.key === "Escape") {
        closeAllDrawers();
      }
      return;
    }

    if (e.key === "Escape") {
      if (isAnyDrawerOpen()) {
        e.preventDefault();
        closeAllDrawers();
        return;
      }
    }

    const lowerKey = e.key.toLowerCase();
    if (lowerKey === "n") {
      e.preventDefault();
      flashAppCard("3201907018807");
      launchApp("3201907018807", "Netflix");
      return;
    }
    if (lowerKey === "y") {
      e.preventDefault();
      flashAppCard("111299001912");
      launchApp("111299001912", "YouTube");
      return;
    }
    if (lowerKey === "a") {
      e.preventDefault();
      flashAppCard("3201910019365");
      launchApp("3201910019365", "Amazon Prime");
      return;
    }
    if (lowerKey === "j") {
      e.preventDefault();
      flashAppCard("3201711015117");
      launchApp("3201711015117", "JioHotstar");
      return;
    }
    if (lowerKey === "i" || lowerKey === "b") {
      e.preventDefault();
      flashAppCard("3201907018784");
      launchApp("3201907018784", "Samsung Internet");
      return;
    }
    if (lowerKey === "s") {
      e.preventDefault();
      flashAppCard("3201606009684");
      launchApp("3201606009684", "Spotify");
      return;
    }

    // Video Seek Shortcuts (Works across all streaming apps)
    if (e.key === "[") {
      e.preventDefault();
      flashSeekButton("-10");
      sendSeek(-10);
      return;
    }
    if (e.key === "]") {
      e.preventDefault();
      flashSeekButton("10");
      sendSeek(10);
      return;
    }
    if (e.key === "<" || e.key === "{" || (e.shiftKey && e.key === "ArrowLeft")) {
      e.preventDefault();
      flashSeekButton("-30");
      sendSeek(-30);
      return;
    }
    if (e.key === ">" || e.key === "}" || (e.shiftKey && e.key === "ArrowRight")) {
      e.preventDefault();
      flashSeekButton("30");
      sendSeek(30);
      return;
    }

    const keyMap = {
      "ArrowUp": "KEY_UP",
      "ArrowDown": "KEY_DOWN",
      "ArrowLeft": "KEY_LEFT",
      "ArrowRight": "KEY_RIGHT",
      "Enter": "KEY_ENTER",
      "Escape": "KEY_RETURN",
      "Backspace": "KEY_RETURN",
      " ": "KEY_PLAYPAUSE",
      "+": "KEY_VOLUP",
      "=": "KEY_VOLUP",
      "-": "KEY_VOLDOWN",
      "_": "KEY_VOLDOWN",
      "m": "KEY_MUTE",
      "M": "KEY_MUTE",
      "h": "KEY_HOME",
      "H": "KEY_HOME",
      "p": "KEY_POWER",
      "P": "KEY_POWER",
      "0": "KEY_0",
      "1": "KEY_1",
      "2": "KEY_2",
      "3": "KEY_3",
      "4": "KEY_4",
      "5": "KEY_5",
      "6": "KEY_6",
      "7": "KEY_7",
      "8": "KEY_8",
      "9": "KEY_9"
    };

    if (keyMap[e.key]) {
      e.preventDefault();
      const tvKey = keyMap[e.key];
      
      const matchingBtn = document.querySelector(`[data-key="${tvKey}"]`);
      if (matchingBtn) {
        matchingBtn.classList.add("is-active");
        setTimeout(() => matchingBtn.classList.remove("is-active"), 150);
      }

      sendKey(tvKey);
    }
  });

  function flashSeekButton(seekSec) {
    const btn = document.querySelector(`.seek-step-btn[data-seek="${seekSec}"]`);
    if (btn) {
      btn.classList.add("is-active");
      setTimeout(() => btn.classList.remove("is-active"), 200);
    }
  }

  function flashAppCard(appId) {
    const card = document.querySelector(`.app-card[data-app-id="${appId}"]`);
    if (card) {
      card.classList.add("app-card-active");
      setTimeout(() => card.classList.remove("app-card-active"), 250);
    }
  }

  // Prevent remote body bounce and scrolling
  window.addEventListener("wheel", (e) => {
    if (!e.target.closest("#discoveryResults, .discovery-results")) {
      e.preventDefault();
    }
  }, { passive: false });

  window.addEventListener("touchmove", (e) => {
    if (!e.target.closest("#discoveryResults, .discovery-results")) {
      e.preventDefault();
    }
  }, { passive: false });

  // Initial poll
  pollStatus();
  setInterval(pollStatus, 5000);
});
