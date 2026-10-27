/* ==============================================================================
   NEKKETSU RETRO AUDIO DECK & DISCIPLINE-AWARE SEAMLESS ROUTER (PJAX)
   - Dynamic Folder Sorting (audio/hub, audio/soccer, audio/quotes, etc.)
   - No hardcoded filenames: accepts ANY user .mp3/.ogg/.wav file!
   - Built-in ID3v1/ID3v2 metadata parser with real-time tag extraction
   ============================================================================== */

(function() {
  if (window.__NEKKETSU_AUDIO_INITED__) return;
  window.__NEKKETSU_AUDIO_INITED__ = true;

  // Resolve base URL relative to this script so it works on any hosting/domain/subfolder
  const SCRIPT_BASE_URL = (document.currentScript && document.currentScript.src) ?
    new URL('.', document.currentScript.src).href :
    (window.location.origin + window.location.pathname.substring(0, window.location.pathname.lastIndexOf('/') + 1));

  function resolveAudioUrl(relPath) {
    if (!relPath) return '';
    if (relPath.startsWith('http://') || relPath.startsWith('https://') || relPath.startsWith('blob:') || relPath.startsWith('data:')) {
      return relPath;
    }
    try {
      return new URL(relPath, SCRIPT_BASE_URL).href;
    } catch(e) {
      return encodeURI(relPath);
    }
  }

  // 1. DEFAULT PLAYLISTS & FOLDER DEFINITIONS
  const DEFAULT_PLAYLISTS = {
    hub: {
      name: "Главный хаб NST (Альманах)",
      badge: "🏛️ ХАБ",
      folder: "audio/hub/",
      tracks: [
        { title: "Nekketsu Koukou - Title Screen (Закиньте .mp3 в audio/hub/)", file: "audio/hub/track_1.mp3", is_placeholder: true },
        { title: "River City Ransom - Main Street (Закиньте .mp3 в audio/hub/)", file: "audio/hub/track_2.mp3", is_placeholder: true }
      ]
    },
    soccer: {
      name: "Футбольная лига Goal 3 (NES)",
      badge: "⚽ ФУТБОЛ",
      folder: "audio/soccer/",
      tracks: [
        { title: "Goal 3 - Match Theme 1 (Закиньте .mp3 в audio/soccer/)", file: "audio/soccer/track_1.mp3", is_placeholder: true },
        { title: "Goal 3 - Match Theme 2 (Закиньте .mp3 в audio/soccer/)", file: "audio/soccer/track_2.mp3", is_placeholder: true },
        { title: "Goal 3 - Tournament Menu (Закиньте .mp3 в audio/soccer/)", file: "audio/soccer/track_3.mp3", is_placeholder: true }
      ]
    },
    quotes: {
      name: "Золотой Цитатник (Chill & Retro)",
      badge: "📜 ЦИТАТНИК",
      folder: "audio/quotes/",
      tracks: [
        { title: "River City Ransom - Cozy Coffee Shop (Закиньте .mp3 в audio/quotes/)", file: "audio/quotes/track_1.mp3", is_placeholder: true },
        { title: "Kunio Downtown - Mellow Stroll (Закиньте .mp3 в audio/quotes/)", file: "audio/quotes/track_2.mp3", is_placeholder: true }
      ]
    },
    hockey: {
      name: "Хоккейная лига (Ike Ike! Nekketsu)",
      badge: "🏒 ХОККЕЙ",
      folder: "audio/hockey/",
      tracks: [
        { title: "Nekketsu Hockey - Battle on Ice (Закиньте .mp3 в audio/hockey/)", file: "audio/hockey/track_1.mp3", is_placeholder: true },
        { title: "Nekketsu Hockey - Period Break (Закиньте .mp3 в audio/hockey/)", file: "audio/hockey/track_2.mp3", is_placeholder: true }
      ]
    },
    basketball: {
      name: "Баскетбол 2х2 (Street Basket)",
      badge: "🏀 БАСКЕТБОЛ",
      folder: "audio/basketball/",
      tracks: [
        { title: "Dunk Heroes - Florida Sun Court (Закиньте .mp3 в audio/basketball/)", file: "audio/basketball/track_1.mp3", is_placeholder: true }
      ]
    },
    fighting: {
      name: "Бои 2х2 (Kakutou Densetsu)",
      badge: "🥊 ДРАКИ 2x2",
      folder: "audio/fighting/",
      tracks: [
        { title: "Kakutou Densetsu - Danger Ring (Закиньте .mp3 в audio/fighting/)", file: "audio/fighting/track_1.mp3", is_placeholder: true }
      ]
    }
  };

  let DISCIPLINE_PLAYLISTS = JSON.parse(JSON.stringify(DEFAULT_PLAYLISTS));

  // Merge auto-manifest if pre-loaded synchronously via <script src="audio/playlist-manifest.js">
  if (window.NEKKETSU_AUDIO_MANIFEST) {
    applyManifest(window.NEKKETSU_AUDIO_MANIFEST);
  } else {
    // Attempt async fetch of playlist.json
    fetch(resolveAudioUrl('audio/playlist.json'))
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (data) {
          applyManifest(data);
          syncDisciplinePlaylist(currentDiscipline, isPlaying);
        }
      })
      .catch(() => {});
  }

  function applyManifest(data) {
    for (const [k, v] of Object.entries(data)) {
      if (DISCIPLINE_PLAYLISTS[k] && v.tracks && v.tracks.length > 0) {
        DISCIPLINE_PLAYLISTS[k].tracks = v.tracks;
      }
    }
    window.NEKKETSU_DISCIPLINES_CONFIG = DISCIPLINE_PLAYLISTS;
  }

  function detectDiscipline(doc = document, url = (window.location.pathname + window.location.search + window.location.hash)) {
    const explicit = doc.body ? doc.body.getAttribute('data-discipline') : null;
    if (explicit && DISCIPLINE_PLAYLISTS[explicit]) return explicit;

    const full = (url || '').toLowerCase();
    if (full.includes('soccer') || full.includes('goal3')) return 'soccer';
    if (full.includes('quote')) return 'quotes';
    if (full.includes('hockey')) return 'hockey';
    if (full.includes('basket')) return 'basketball';
    if (full.includes('fight') || full.includes('kakutou')) return 'fighting';
    return 'hub';
  }

  let currentDiscipline = detectDiscipline();
  let currentPlaylist = (DISCIPLINE_PLAYLISTS[currentDiscipline] || DISCIPLINE_PLAYLISTS.hub).tracks;
  let currentTrackIdx = 0;
  let isPlaying = false;
  let audioEl = null;

  // 2. REAL-TIME ID3 METADATA PARSER (PURE CLIENT-SIDE JS)
  const id3Cache = new Map();

  async function inspectTrackMetadata(track) {
    if (!track || !track.file || track.is_placeholder || track._metaChecked) return;
    track._metaChecked = true;

    if (id3Cache.has(track.file)) {
      const cached = id3Cache.get(track.file);
      if (cached && (cached.title || cached.artist)) {
        track.title = cached.artist ? `${cached.artist} - ${cached.title}` : cached.title;
        updateUI();
        renderPlaylistItems();
      }
      return;
    }

    try {
      const response = await fetch(resolveAudioUrl(track.file), {
        headers: { Range: 'bytes=0-8191' }
      });
      if (!response.ok && response.status !== 206) return;

      const buffer = await response.arrayBuffer();
      const meta = parseID3v2(buffer);

      if (meta && (meta.title || meta.artist)) {
        id3Cache.set(track.file, meta);
        const artist = meta.artist ? meta.artist.trim() : '';
        const title = meta.title ? meta.title.trim() : '';
        track.title = artist && title ? `${artist} - ${title}` : (title || artist);
        updateUI();
        renderPlaylistItems();
      }
    } catch (e) {
      // Range requests might not be supported on some basic hosts; fallback cleanly
    }
  }

  function parseID3v2(buffer) {
    const bytes = new Uint8Array(buffer);
    if (bytes.length < 10) return null;
    // Check ID3 header: 'I', 'D', '3'
    if (bytes[0] !== 0x49 || bytes[1] !== 0x44 || bytes[2] !== 0x33) return null;

    const major = bytes[3];
    const tagSize = ((bytes[6] & 0x7F) << 21) | ((bytes[7] & 0x7F) << 14) | ((bytes[8] & 0x7F) << 7) | (bytes[9] & 0x7F);
    
    let offset = 10;
    const maxOffset = Math.min(bytes.length, 10 + tagSize);
    const result = {};

    while (offset < maxOffset - 10) {
      if (bytes[offset] === 0) break; // Padding
      const frameId = String.fromCharCode(bytes[offset], bytes[offset+1], bytes[offset+2], bytes[offset+3]);
      
      let frameSize = 0;
      if (major === 4) {
        frameSize = ((bytes[offset+4] & 0x7F) << 21) | ((bytes[offset+5] & 0x7F) << 14) | ((bytes[offset+6] & 0x7F) << 7) | (bytes[offset+7] & 0x7F);
      } else {
        frameSize = (bytes[offset+4] << 24) | (bytes[offset+5] << 16) | (bytes[offset+6] << 8) | bytes[offset+7];
      }

      const headerSize = 10;
      if (frameSize <= 0 || offset + headerSize + frameSize > bytes.length) break;

      const encoding = bytes[offset + headerSize];
      const frameData = bytes.subarray(offset + headerSize + 1, offset + headerSize + frameSize);
      
      let text = '';
      try {
        if (encoding === 0) {
          text = new TextDecoder('windows-1251').decode(frameData);
        } else if (encoding === 1) {
          text = new TextDecoder('utf-16').decode(frameData);
        } else if (encoding === 2) {
          text = new TextDecoder('utf-16be').decode(frameData);
        } else {
          text = new TextDecoder('utf-8').decode(frameData);
        }
        text = text.replace(/\0+$/, '').trim();
      } catch(e) {
        try {
          text = new TextDecoder('utf-8').decode(frameData).replace(/\0+$/, '').trim();
        } catch(e2) {}
      }

      if (frameId === 'TIT2' && text) result.title = text;
      if (frameId === 'TPE1' && text) result.artist = text;
      if (frameId === 'TALB' && text) result.album = text;

      offset += headerSize + frameSize;
    }

    return (result.title || result.artist) ? result : null;
  }

  // 3. CREATE AUDIO ELEMENT
  function initAudio() {
    if (audioEl) return;
    audioEl = document.createElement('audio');
    audioEl.id = 'nekketsu-master-audio';
    audioEl.preload = 'metadata';
    audioEl.volume = parseFloat(localStorage.getItem('nekketsu_vol') || '0.7');

    audioEl.addEventListener('ended', nextTrack);
    audioEl.addEventListener('error', handleAudioError);
    audioEl.addEventListener('timeupdate', () => {
      if (audioEl && isPlaying) {
        localStorage.setItem('nekketsu_track_time', audioEl.currentTime.toString());
      }
    });

    document.body.appendChild(audioEl);
    loadTrack(currentTrackIdx, false);
  }

  // 4. BUILD UI DECK
  function buildDeckUI() {
    if (document.getElementById('nekketsu-audio-deck')) return;

    const discData = DISCIPLINE_PLAYLISTS[currentDiscipline] || DISCIPLINE_PLAYLISTS.hub;

    const deck = document.createElement('div');
    deck.id = 'nekketsu-audio-deck';

    deck.innerHTML = `
      <div class="deck-controls-group">
        <button class="deck-btn" id="deckPrevBtn" title="Предыдущий трек">⏮</button>
        <button class="deck-btn deck-btn-play" id="deckPlayBtn" title="Воспроизведение / Пауза">▶</button>
        <button class="deck-btn" id="deckNextBtn" title="Следующий трек">⏭</button>
        <div class="deck-equalizer" id="deckEq">
          <div class="eq-bar"></div>
          <div class="eq-bar"></div>
          <div class="eq-bar"></div>
          <div class="eq-bar"></div>
        </div>
      </div>

      <div class="deck-track-info">
        <span class="deck-track-badge" id="deckTrackBadge">${discData.badge}</span>
        <span class="deck-track-title" id="deckTrackTitle">Загрузка...</span>
      </div>

      <div class="deck-right-group">
        <span style="font-size: 13px;" class="deck-vol-label">🔈</span>
        <input type="range" class="deck-vol-slider" id="deckVol" min="0" max="1" step="0.05" value="${audioEl ? audioEl.volume : 0.7}" title="Громкость">
        <button class="deck-btn" id="deckPlaylistBtn" title="Список треков">📋 ТРЕКИ</button>
      </div>

      <div id="deck-playlist-modal">
        <div class="playlist-header">
          <span id="deckPlaylistTitle">🎵 ${discData.name.toUpperCase()}</span>
          <span style="cursor: pointer;" id="deckClosePlaylist">✖</span>
        </div>
        <div id="deckPlaylistItems"></div>
      </div>
    `;

    document.body.appendChild(deck);

    // Event listeners
    document.getElementById('deckPlayBtn').addEventListener('click', togglePlay);
    document.getElementById('deckPrevBtn').addEventListener('click', prevTrack);
    document.getElementById('deckNextBtn').addEventListener('click', nextTrack);
    
    const volSlider = document.getElementById('deckVol');
    volSlider.addEventListener('input', (e) => {
      const v = parseFloat(e.target.value);
      if (audioEl) audioEl.volume = v;
      localStorage.setItem('nekketsu_vol', v.toString());
    });

    const plBtn = document.getElementById('deckPlaylistBtn');
    const plModal = document.getElementById('deck-playlist-modal');
    plBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      plModal.classList.toggle('open');
      renderPlaylistItems();
    });

    document.getElementById('deckClosePlaylist').addEventListener('click', () => {
      plModal.classList.remove('open');
    });

    document.addEventListener('click', (e) => {
      if (!plModal.contains(e.target) && e.target !== plBtn) {
        plModal.classList.remove('open');
      }
    });

    updateUI();
  }

  function renderPlaylistItems() {
    const list = document.getElementById('deckPlaylistItems');
    if (!list) return;

    if (!currentPlaylist || currentPlaylist.length === 0) {
      list.innerHTML = `<div style="padding: 12px; color: #94a3b8; font-size: 12px; text-align: center;">Папка пуста. Закиньте .mp3 файлы!</div>`;
      return;
    }

    list.innerHTML = currentPlaylist.map((t, idx) => `
      <div class="playlist-item ${idx === currentTrackIdx ? 'active' : ''}" data-idx="${idx}">
        <span>${idx + 1}. ${t.title}</span>
        <span style="font-size: 11px; opacity: 0.7;">${idx === currentTrackIdx && isPlaying ? '▶' : ''}</span>
      </div>
    `).join('');

    list.querySelectorAll('.playlist-item').forEach(el => {
      el.addEventListener('click', () => {
        const idx = parseInt(el.getAttribute('data-idx'), 10);
        currentTrackIdx = idx;
        loadTrack(idx, true);
        renderPlaylistItems();
      });
    });
  }

  function loadTrack(idx, autoPlay = true) {
    if (!currentPlaylist || currentPlaylist.length === 0) return;
    if (idx < 0) idx = currentPlaylist.length - 1;
    if (idx >= currentPlaylist.length) idx = 0;
    currentTrackIdx = idx;

    const track = currentPlaylist[idx];
    if (audioEl) {
      audioEl.src = resolveAudioUrl(track.file);
      inspectTrackMetadata(track);

      if (autoPlay) {
        audioEl.play().then(() => {
          isPlaying = true;
          updateUI();
        }).catch(err => {
          console.warn("Autoplay waiting for user gesture:", err);
          isPlaying = false;
          updateUI();
        });
      }
    }
    updateUI();
  }

  function togglePlay() {
    if (!audioEl) return;
    if (isPlaying) {
      audioEl.pause();
      isPlaying = false;
      updateUI();
    } else {
      const curTrack = currentPlaylist[currentTrackIdx];
      if (curTrack && curTrack.is_placeholder) {
        playSyntheticChime();
        return;
      }
      audioEl.play().then(() => {
        isPlaying = true;
        updateUI();
      }).catch(err => {
        console.warn("Audio play prevented:", err);
        playSyntheticChime(); // Play 8-bit retro chime if file not yet uploaded
      });
    }
  }

  function prevTrack() {
    loadTrack(currentTrackIdx - 1, true);
  }

  function nextTrack() {
    loadTrack(currentTrackIdx + 1, true);
  }

  function updateUI() {
    const track = currentPlaylist[currentTrackIdx] || { title: "Трек" };
    const titleEl = document.getElementById('deckTrackTitle');
    if (titleEl) titleEl.textContent = track.title;

    const discData = DISCIPLINE_PLAYLISTS[currentDiscipline] || DISCIPLINE_PLAYLISTS.hub;
    const badgeEl = document.getElementById('deckTrackBadge');
    if (badgeEl) badgeEl.textContent = discData.badge || '8-BIT BGM';

    const playBtn = document.getElementById('deckPlayBtn');
    const eq = document.getElementById('deckEq');
    if (playBtn) {
      if (isPlaying) {
        playBtn.textContent = '⏸';
        playBtn.classList.add('playing');
        playBtn.title = 'Пауза';
        if (eq) eq.classList.add('active');
      } else {
        playBtn.textContent = '▶';
        playBtn.classList.remove('playing');
        playBtn.title = 'Воспроизведение';
        if (eq) eq.classList.remove('active');
      }
    }
  }

  function syncDisciplinePlaylist(newDiscipline, forcePlay = null) {
    if (newDiscipline === currentDiscipline && currentPlaylist && currentPlaylist.length > 0) {
      return; // Same discipline - do not interrupt currently playing music!
    }

    currentDiscipline = newDiscipline;
    const discData = DISCIPLINE_PLAYLISTS[currentDiscipline] || DISCIPLINE_PLAYLISTS.hub;
    currentPlaylist = discData.tracks;
    currentTrackIdx = 0;

    const plTitleEl = document.getElementById('deckPlaylistTitle');
    if (plTitleEl) plTitleEl.textContent = `🎵 ${discData.name.toUpperCase()}`;

    const shouldPlay = (forcePlay !== null) ? forcePlay : isPlaying;
    loadTrack(0, shouldPlay);
    renderPlaylistItems();
  }

  // 8-bit Audio synthesizer fallback if mp3 files are not yet uploaded
  function playSyntheticChime() {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      if (ctx.state === 'suspended') ctx.resume();

      const notes = [523.25, 659.25, 783.99, 1046.50]; // C5, E5, G5, C6
      notes.forEach((freq, i) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'square';
        osc.frequency.setValueAtTime(freq, ctx.currentTime + i * 0.12);
        gain.gain.setValueAtTime(0.1, ctx.currentTime + i * 0.12);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + i * 0.12 + 0.2);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(ctx.currentTime + i * 0.12);
        osc.stop(ctx.currentTime + i * 0.12 + 0.25);
      });
      const cur = currentPlaylist[currentTrackIdx];
      const titleEl = document.getElementById('deckTrackTitle');
      if (titleEl) {
        titleEl.textContent = `♫ [8-Bit Chime] Закиньте MP3 в ${DISCIPLINE_PLAYLISTS[currentDiscipline].folder} ♫`;
      }
    } catch (e) {
      console.log(e);
    }
  }

  function handleAudioError(e) {
    const curTrack = currentPlaylist[currentTrackIdx];
    console.info(`Audio track not found: ${curTrack ? curTrack.file : ''}`);
    const titleEl = document.getElementById('deckTrackTitle');
    if (titleEl) {
      titleEl.textContent = `[Файл не найден] Закиньте MP3 в ${DISCIPLINE_PLAYLISTS[currentDiscipline].folder}`;
    }
    isPlaying = false;
    updateUI();
  }

  // 5. BOOTSTRAP DECK ON DOM READY
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      initAudio();
      buildDeckUI();
    });
  } else {
    initAudio();
    buildDeckUI();
  }
})();
