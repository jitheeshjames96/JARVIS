/* JARVIS browser voice — conversational GCP API, clap, session, actions */
(function () {
  const API = window.JARVIS_API || '';
  const AGENT = window.JARVIS_AGENT || null;
  const HUD_HOME = window.JARVIS_HUD || 'https://storage.googleapis.com/jarvis-jitheesh-2026/dashboard.html';

  let recognition = null;
  let listening = false;
  let sessionActive = false;
  let clapWatchActive = false;
  let audioCtx = null;
  let clapStream = null;
  let convSession = {};

  function setHubState(state) {
    const hub = document.querySelector('.hub-wrap');
    if (hub) {
      hub.classList.remove('listening', 'processing', 'speaking', 'idle', 'session');
      if (state) hub.classList.add(state);
    }
    const mic = document.getElementById('voice-mic');
    if (mic) mic.classList.toggle('listening', state === 'listening' || state === 'session');
    const badge = document.getElementById('voice-status');
    if (badge) badge.textContent = sessionActive ? 'SESSION' : (state ? state.toUpperCase() : 'ONLINE');
    const clapBadge = document.getElementById('clap-status');
    if (clapBadge) clapBadge.textContent = clapWatchActive ? 'CLAP ON' : 'CLAP OFF';
    const agentBadge = document.getElementById('active-agent');
    if (agentBadge) {
      const a = convSession.last_agent || AGENT || 'jarvis';
      agentBadge.textContent = a.toUpperCase();
    }
  }

  function speakBrowser(text, onEnd) {
    if (!window.speechSynthesis || !text) { if (onEnd) onEnd(); return; }
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.rate = 1.0;
    u.lang = 'en-IN';
    u.onstart = () => setHubState(sessionActive ? 'session' : 'speaking');
    u.onend = () => {
      if (sessionActive) { setHubState('session'); resumeSessionListen(); }
      else setHubState('idle');
      if (onEnd) onEnd();
    };
    window.speechSynthesis.speak(u);
  }

  function esc(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  function showTranscript(user, jarvis, links, handoff) {
    const box = document.getElementById('voice-log');
    if (!box) return;
    let linksHtml = '';
    if (links && links.length) {
      linksHtml = '<div class="v-links">' + links.map((l) =>
        `<a href="${esc(l.url)}" target="_blank" rel="noopener">${esc(l.label || 'Open')}</a>`
      ).join(' · ') + '</div>';
    }
    const handoffHtml = handoff ? `<span class="v-handoff">↪ ${esc(handoff)}</span> ` : '';
    const line = document.createElement('div');
    line.className = 'vlog-line';
    line.innerHTML = user
      ? `<span class="v-you">YOU</span> ${esc(user)}<br><span class="v-j">JARVIS</span> ${handoffHtml}${esc(jarvis)}${linksHtml}`
      : `<span class="v-j">JARVIS</span> ${esc(jarvis)}`;
    box.prepend(line);
    while (box.children.length > 14) box.removeChild(box.lastChild);
  }

  function normalize(text) {
    let t = text.trim();
    for (const prefix of ['hey jarvis', 'ok jarvis', 'jarvis', 'hey', 'ok']) {
      if (t.toLowerCase().startsWith(prefix)) {
        t = t.slice(prefix.length).trim().replace(/^[,.\s!-]+/, '');
        break;
      }
    }
    return t;
  }

  function isStandDown(text) { return /stand\s*down/i.test(text); }

  function handleActions(data) {
    const action = data.action;
    if (action === 'navigate_home') {
      convSession = {};
      const target = data.url || HUD_HOME;
      if (!window.location.href.includes('dashboard.html')) {
        window.location.href = target;
      } else {
        showTranscript('', 'Main JARVIS ready. What do you need?');
        speakBrowser('Main JARVIS ready. What do you need?');
        if (typeof closeHudTab === 'function') closeHudTab();
      }
      return true;
    }
    if (action === 'open_url' && data.url) {
      window.open(data.url, '_blank', 'noopener');
      return true;
    }
    if (action === 'open_tab' && data.tab && typeof openHudTab === 'function') {
      openHudTab(data.tab);
      return true;
    }
    if (action === 'end_session') return false;
    return false;
  }

  async function sendCommand(text) {
    const cmd = normalize(text);
    if (!cmd) return;

    if (isStandDown(cmd)) {
      endSession('Standing down. Clap when you need me again.');
      convSession = {};
      return;
    }

    if (!API) {
      showTranscript(cmd, 'Voice API not configured.');
      return;
    }

    setHubState('processing');
    showTranscript(cmd, '…');
    try {
      const res = await fetch(API, {
        method: 'POST',
        mode: 'cors',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: cmd, agent: AGENT, session: convSession }),
      });
      const data = await res.json();
      const reply = data.response || data.error || 'No response.';
      if (data.session) convSession = data.session;
      if (data.active_agent) convSession.last_agent = data.active_agent;

      showTranscript(cmd, reply, data.links, data.handoff);
      const navigated = handleActions(data);
      if (!navigated) speakBrowser(reply);
      if (data.tab && typeof openHudTab === 'function' && !navigated) {
        setTimeout(() => openHudTab(data.tab), 800);
      }
    } catch (e) {
      showTranscript(cmd, 'Cannot reach GCP voice API.');
      setHubState(sessionActive ? 'session' : 'idle');
      if (sessionActive) resumeSessionListen();
    }
  }

  function resumeSessionListen() {
    if (!sessionActive || !recognition) return;
    recognition.continuous = true;
    try { recognition.start(); } catch (_) {}
  }

  function startSession(fromClap) {
    if (sessionActive) return;
    sessionActive = true;
    setHubState('session');
    const guide = AGENT
      ? `Yes? ${AGENT.toUpperCase()} channel. Ask anything — follow-ups work. Say return home or stand down.`
      : "Yes? I'm listening. Ask market, family by name, news, or charts. Follow-ups work. Say stand down to end.";
    showTranscript('', fromClap ? '👏 Clap detected' : '🎤 Session started');
    speakBrowser(guide, () => {
      if (!recognition) return;
      recognition.continuous = true;
      try { recognition.start(); } catch (_) {}
    });
    updateHint();
  }

  function endSession(msg) {
    sessionActive = false;
    if (recognition) {
      try { recognition.stop(); } catch (_) {}
      recognition.continuous = false;
    }
    setHubState('idle');
    if (msg) { showTranscript('', msg); speakBrowser(msg); }
    updateHint();
  }

  function updateHint() {
    const hint = document.getElementById('voice-hint');
    if (!hint) return;
    if (sessionActive) {
      hint.textContent = 'Session active — follow-ups OK · "return home" · "stand down" to end';
    } else if (clapWatchActive) {
      hint.textContent = 'Clap to wake · V for session · ask by name (Rosamma, MARUTI, Kerala news)';
    } else {
      hint.textContent = 'Clap or press V · conversational follow-ups enabled';
    }
  }

  async function initClapWatch() {
    if (!navigator.mediaDevices?.getUserMedia) return;
    try {
      clapStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const src = audioCtx.createMediaStreamSource(clapStream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 512;
      src.connect(analyser);
      const data = new Uint8Array(analyser.fftSize);
      let baseline = 0.02;
      let lastClap = 0;
      clapWatchActive = true;
      updateHint();
      function loop() {
        if (!clapWatchActive) return;
        analyser.getByteTimeDomainData(data);
        let peak = 0, sum = 0;
        for (let i = 0; i < data.length; i++) {
          const v = Math.abs(data[i] - 128) / 128;
          sum += v;
          if (v > peak) peak = v;
        }
        const rms = sum / data.length;
        baseline = baseline * 0.98 + rms * 0.02;
        const threshold = Math.max(0.18, baseline * 3.5);
        const now = Date.now();
        if (peak > threshold && now - lastClap > 900) {
          lastClap = now;
          if (!sessionActive && !listening) startSession(true);
        }
        requestAnimationFrame(loop);
      }
      loop();
    } catch (e) {
      const hint = document.getElementById('voice-hint');
      if (hint) hint.textContent = 'Allow microphone for clap + voice';
    }
  }

  function initVoice() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    const btn = document.getElementById('voice-mic');
    const hint = document.getElementById('voice-hint');
    const input = document.getElementById('cmd-input');
    const send = document.getElementById('cmd-send');
    const clapToggle = document.getElementById('clap-toggle');

    if (input && send) {
      send.addEventListener('click', () => {
        const t = input.value.trim();
        if (t) { sendCommand(t); input.value = ''; }
      });
      input.addEventListener('keydown', (e) => { if (e.key === 'Enter') send.click(); });
    }

    if (clapToggle) {
      clapToggle.addEventListener('click', () => {
        if (clapWatchActive) {
          clapWatchActive = false;
          if (clapStream) clapStream.getTracks().forEach((t) => t.stop());
          updateHint();
        } else initClapWatch();
      });
    }

    if (!SR) {
      if (hint) hint.textContent += ' · Type commands';
      initClapWatch();
      return;
    }

    recognition = new SR();
    recognition.lang = 'en-IN';
    recognition.interimResults = false;
    recognition.continuous = false;

    recognition.onstart = () => {
      listening = true;
      setHubState(sessionActive ? 'session' : 'listening');
    };
    recognition.onend = () => {
      listening = false;
      if (sessionActive) setTimeout(resumeSessionListen, 300);
      else if (!document.querySelector('.hub-wrap.speaking')) { setHubState('idle'); updateHint(); }
    };
    recognition.onerror = (ev) => {
      if (sessionActive && ev.error === 'no-speech') { resumeSessionListen(); return; }
      setHubState(sessionActive ? 'session' : 'idle');
    };
    recognition.onresult = (ev) => {
      const last = ev.results.length - 1;
      if (!ev.results[last].isFinal) return;
      const text = ev.results[last][0].transcript.trim();
      if (text) sendCommand(text);
    };

    function toggleListen() {
      if (!API) return;
      if (sessionActive) { endSession('Session ended.'); return; }
      if (listening) { recognition.stop(); return; }
      startSession(false);
    }

    if (btn) btn.addEventListener('click', toggleListen);
    document.addEventListener('keydown', (e) => {
      if (e.key === 'v' || e.key === 'V') { e.preventDefault(); toggleListen(); }
    });

    initClapWatch();
    updateHint();
  }

  document.addEventListener('DOMContentLoaded', initVoice);
})();
