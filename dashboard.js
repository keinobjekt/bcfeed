// Fetch runtime config before bootstrapping the app.
    window.BC_CONFIG_PROMISE = fetch("config.json", { cache: "no-store" })
      .then(resp => resp.ok ? resp.json() : {})
      .catch(() => ({}));

(async () => {
    let releases = [];
    const releaseMap = new Map();
    let embedProxyUrl = "http://localhost:5050/embed-meta";
    let apiRoot = embedProxyUrl ? embedProxyUrl.replace(/\/embed-meta.*$/, "") : null;
    const apiHost = (() => {
      try {
        return apiRoot ? new URL(apiRoot).hostname : null;
      } catch {
        return null;
      }
    })();
    let healthUrl = apiRoot ? `${apiRoot}/health` : null;
    let clearCredsUrl = apiRoot ? `${apiRoot}/clear-credentials` : null;
    let loadCredsUrl = apiRoot ? `${apiRoot}/load-credentials` : null;
    let starredApi = apiRoot ? `${apiRoot}/starred-state` : null;
    let clearStatusOnLoad = false;
    let showDevSettings = false;
    let missingToken = false;
    const serverDownBackdrop = document.getElementById("server-down-backdrop");
    const maxResultsBackdrop = document.getElementById("max-results-backdrop");
    const missingTokenBackdrop = document.getElementById("missing-token-backdrop");
    const missingTokenClose = document.getElementById("missing-token-close");
    const missingTokenContinue = document.getElementById("missing-token-continue");
    let serverDownShown = false;
    let maxNoticeShown = false;
    let defaultTheme = "light";
    const populateLog = document.getElementById("populate-log");
    const clearCredsBtn = document.getElementById("clear-creds-btn");
    const loadCredsBtn = document.getElementById("load-creds-btn");
    const loadCredsFile = document.getElementById("load-creds-file");
    const loadCredsBackdrop = document.getElementById("load-creds-backdrop");
    const loadCredsClose = document.getElementById("load-creds-close");
    const loadCredsContinue = document.getElementById("load-creds-continue");
    const asBool = (val) => {
      if (typeof val === "boolean") return val;
      if (val == null) return false;
      if (typeof val === "number") return !!val;
      if (typeof val === "string") return ["1","true","yes","on"].includes(val.trim().toLowerCase());
      return false;
    };
    const config = await (window.BC_CONFIG_PROMISE || Promise.resolve({}));
    const proxyCandidate = (config && config.embed_proxy_url) ? String(config.embed_proxy_url) : embedProxyUrl;
    const normalizedProxy = proxyCandidate ? proxyCandidate.replace(/\/+$/, "") : "";
    embedProxyUrl = normalizedProxy || null;
    apiRoot = embedProxyUrl ? embedProxyUrl.replace(/\/embed-meta.*$/, "") : null;
    healthUrl = apiRoot ? `${apiRoot}/health` : null;
    clearCredsUrl = apiRoot ? `${apiRoot}/clear-credentials` : null;
    loadCredsUrl = apiRoot ? `${apiRoot}/load-credentials` : null;
    starredApi = apiRoot ? `${apiRoot}/starred-state` : null;
    if (config && config.default_theme) defaultTheme = config.default_theme;
    if (config && typeof config.clear_status_on_load !== "undefined") {
      clearStatusOnLoad = asBool(config.clear_status_on_load);
    }
    if (config && typeof config.show_dev_settings !== "undefined") {
      showDevSettings = asBool(config.show_dev_settings);
    }
    if (config && typeof config.has_credentials !== "undefined") {
      missingToken = !asBool(config.has_credentials);
    } else if (config && typeof config.has_token !== "undefined") {
      // Fallback for backward compatibility
      missingToken = !asBool(config.has_token);
    }
    const loadingState = document.getElementById("loading-state");
    const errorState = document.getElementById("error-state");
    function applyDevSettingsVisibility() {
      const devEls = document.querySelectorAll(".dev-setting");
      devEls.forEach((el) => {
        el.style.display = showDevSettings ? "" : "none";
      });
    }
    if (populateLog && clearStatusOnLoad) {
      populateLog.textContent = "Select a date range to display.";
    }
    applyDevSettingsVisibility();
    function releaseKey(release) {
      return release.url || [release.page_name, release.artist, release.title, release.date].filter(Boolean).join("|");
    }
    function setLoading(message = "Loading releases…") {
      if (loadingState) {
        loadingState.textContent = message;
        loadingState.style.display = "flex";
      }
      if (errorState) errorState.style.display = "none";
    }
    function hideLoading() {
      if (loadingState) loadingState.style.display = "none";
    }
    function showError(message) {
      hideLoading();
      if (errorState) {
        errorState.textContent = message || "Failed to load releases. Is the bcfeed proxy running?";
        errorState.style.display = "flex";
      }
      const tableWrapper = document.querySelector(".table-wrapper");
      if (tableWrapper) tableWrapper.style.display = "none";
      const wireframe = document.getElementById("scrape-wireframe");
      if (wireframe) wireframe.style.display = "none";
    }
    async function loadViewedSet() {
      if (!apiRoot) throw new Error("Proxy not configured");
      const resp = await fetch(`${apiRoot}/viewed-state`);
      if (!resp.ok) throw new Error(`Viewed state unavailable (HTTP ${resp.status})`);
      const data = await resp.json();
      if (data && Array.isArray(data.viewed)) {
        return new Set(data.viewed);
      }
      return new Set();
    }
    async function loadStarredSet() {
      if (!starredApi) throw new Error("Proxy not configured");
      const resp = await fetch(starredApi);
      if (!resp.ok) throw new Error(`Starred state unavailable (HTTP ${resp.status})`);
      const data = await resp.json();
      if (data && Array.isArray(data.starred)) {
        return new Set(data.starred);
      }
      return new Set();
    }
    async function fetchReleases() {
      if (!apiRoot) throw new Error("Proxy not configured");
      const resp = await fetch(`${apiRoot}/releases`, { cache: "no-store" });
      if (!resp.ok) throw new Error(`Failed to load releases (HTTP ${resp.status})`);
      const data = await resp.json();
      const list = Array.isArray(data.releases) ? data.releases : [];
      releases = list;
      releaseMap.clear();
      list.forEach(r => releaseMap.set(releaseKey(r), r));
    }
    function showServerDownModal() {
      if (serverDownShown) return;
      serverDownShown = true;
      if (serverDownBackdrop) {
        serverDownBackdrop.style.display = "flex";
      }
    }
    function showMaxResultsModal() {
      if (maxResultsBackdrop) {
        maxResultsBackdrop.style.display = "flex";
      }
    }
    function hideMaxResultsModal() {
      if (maxResultsBackdrop) {
        maxResultsBackdrop.style.display = "none";
      }
    }
    function appendPopulateLogLine(msg) {
      if (!populateLog) return;
      const current = populateLog.textContent || "";
      const next = current ? `${current}\n${msg}` : msg;
      populateLog.textContent = next;
      populateLog.scrollTop = populateLog.scrollHeight;
    }
    async function checkServerAlive() {
      if (!healthUrl || serverDownShown) return;
      const online = typeof navigator === "undefined" ? true : navigator.onLine;
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 4000);
      try {
        const resp = await fetch(healthUrl, {
          method: "GET",
          cache: "no-store",
          signal: controller.signal,
        });
        clearTimeout(timer);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      } catch (err) {
        clearTimeout(timer);
        if (!online) {
          // Ignore offline blips; try again on next interval.
          return;
        }
        const isLocalHost = apiHost && ["localhost", "127.0.0.1", location.hostname].includes(apiHost);
        if (!isLocalHost) {
          // Only count failures for remote hosts if the response was non-OK.
          return;
        }
        showServerDownModal();
      }
    }
    async function persistViewedRemote(url, isRead) {
      if (!apiRoot || !url) return;
      try {
        await fetch(`${apiRoot}/viewed-state`, {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({url, read: isRead}),
        });
      } catch (err) {
        console.warn("Failed to persist viewed state to API", err);
      }
    }
    async function persistStarredRemote(url, starred) {
      if (!starredApi || !url) return;
      try {
        await fetch(starredApi, {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({url, starred}),
        });
      } catch (err) {
        console.warn("Failed to persist starred state to API", err);
      }
    }
    function setViewed(release, isRead) {
      const key = releaseKey(release);
      if (!key) return;
      if (isRead) {
        state.viewed.add(key);
      } else {
        state.viewed.delete(key);
      }
      persistViewedRemote(release.url || key, isRead);
      renderCalendar("range");
    }
    function updateStarButton(button, isStarred) {
      if (!button) return;
      button.classList.toggle("starred", isStarred);
      button.setAttribute("aria-pressed", String(isStarred));
      button.title = isStarred ? "Unstar this release" : "Star this release";
      button.setAttribute("aria-label", button.title);
    }
    function markCachedBadge(row, release) {
      if (!row || !state.showCachedBadges) return;
      const titleCell = row.querySelector("[data-title-cell]");
      if (titleCell && release.embed_url && !titleCell.querySelector(".cached-badge")) {
        titleCell.insertAdjacentHTML("beforeend", ' <span class="cached-badge">cached</span>');
      }
    }
    function setStarred(release, isStarred, opts = { row: null, button: null }) {
      const rowEl = opts.row || null;
      const btn = opts.button || null;
      const key = releaseKey(release);
      if (!key) return;
      if (isStarred) {
        state.starred.add(key);
      } else {
        state.starred.delete(key);
      }
      persistStarredRemote(release.url || key, isStarred);
      if (rowEl) {
        rowEl.classList.toggle("starred", isStarred);
      }
      if (btn) {
        updateStarButton(btn, isStarred);
      }
      if (isStarred) {
        ensureEmbed(release).then((embedUrl) => {
          if (embedUrl && rowEl) {
            markCachedBadge(rowEl, release);
          }
        });
      }
    }
    const state = {
      sortKey: "date",
      direction: "desc",
      showLabels: new Set(),
      showOnlyLabels: new Set(),
      viewed: new Set(),
      starred: new Set(),
      showOnlyStarred: false,
      hideViewed: false,
      hideViewedSnapshot: new Set(),
      expandedKey: null,
      dateFilterFrom: "",
      dateFilterTo: "",
      filterByDate: true,
      showCachedBadges: true,
    };
    let lastLabelSignature = "";
    const THEME_KEY = "bc_dashboard_theme";
    const SHOW_CACHED_KEY = "bc_show_cached_badges";
    const themeToggleBtn = document.getElementById("theme-toggle");
    function applyTheme(theme) {
      const isLight = theme === "light";
      document.body.classList.toggle("theme-light", isLight);
      if (themeToggleBtn) {
        themeToggleBtn.checked = !isLight;
      }
      localStorage.setItem(THEME_KEY, isLight ? "light" : "dark");
    }
    const savedThemeValue = localStorage.getItem(THEME_KEY);
    let savedTheme = savedThemeValue || defaultTheme || "light";
    if (!showDevSettings && !savedThemeValue) {
      savedTheme = "dark";
    }
    applyTheme(savedTheme);
    if (themeToggleBtn) {
      themeToggleBtn.checked = savedTheme !== "light";
      themeToggleBtn.addEventListener("change", () => {
        const next = themeToggleBtn.checked ? "dark" : "light";
        applyTheme(next);
      });
    }
    if (!showDevSettings) {
      state.showCachedBadges = true;
      try { localStorage.setItem(SHOW_CACHED_KEY, "true"); } catch (e) {}
      const cachedToggle = document.getElementById("show-cached-toggle");
      if (cachedToggle) cachedToggle.checked = true;
    }
    if (clearCredsBtn && clearCredsUrl) {
      clearCredsBtn.addEventListener("click", async () => {
        clearCredsBtn.disabled = true;
        const original = clearCredsBtn.textContent;
        clearCredsBtn.textContent = "Clearing…";
        try {
          const resp = await fetch(clearCredsUrl, { method: "POST" });
          const data = await resp.json().catch(() => ({}));
          const joinedLogs = Array.isArray(data.logs) ? data.logs.join("\n") : "";
          if (!resp.ok) {
            const msg = data.error || "Failed to clear credentials.";
            const next = joinedLogs ? `${msg}\n${joinedLogs}` : msg;
            if (populateLog) populateLog.textContent = next;
            alert(msg);
          } else {
            const msg = joinedLogs || "Credentials reloaded.";
            if (populateLog) populateLog.textContent = msg;
          }
        } catch (err) {
          const msg = String(err || "Failed to load credentials.");
          if (populateLog) populateLog.textContent = msg;
          alert(msg);
        } finally {
          clearCredsBtn.disabled = false;
          clearCredsBtn.textContent = original || "Clear credentials";
        }
      });
    }
    if (loadCredsBtn && loadCredsFile && loadCredsUrl) {
      const doLoadCreds = async () => {
        const file = loadCredsFile.files && loadCredsFile.files[0];
        if (!file) return;
        loadCredsBtn.disabled = true;
        const original = loadCredsBtn.textContent;
        loadCredsBtn.textContent = "Loading…";
        try {
          const form = new FormData();
          form.append("file", file, file.name);
          const resp = await fetch(loadCredsUrl, {
            method: "POST",
            body: form,
          });
          const data = await resp.json().catch(() => ({}));
          const joinedLogs = Array.isArray(data.logs) ? data.logs.join("\n") : "";
          if (!resp.ok) {
            const msg = data.error || "Failed to load credentials.";
            const next = joinedLogs ? `${msg}\n${joinedLogs}` : msg;
            if (populateLog) populateLog.textContent = next;
            alert(msg);
          } else {
            const msg = joinedLogs || "Credentials loaded and authenticated.";
            if (populateLog) populateLog.textContent = msg;
            alert("Credentials loaded.");
          }
        } catch (err) {
          const msg = String(err || "Failed to load credentials.");
          if (populateLog) populateLog.textContent = msg;
          alert(msg);
        } finally {
          loadCredsBtn.disabled = false;
          loadCredsBtn.textContent = original || "Load credentials";
        }
      };
      const openLoadCredsFile = () => {
        if (loadCredsFile) {
          loadCredsFile.value = "";
          loadCredsFile.click();
        }
      };
      const showLoadCredsModal = () => {
        if (loadCredsBackdrop) {
          loadCredsBackdrop.style.display = "flex";
        } else {
          openLoadCredsFile();
        }
      };
      const hideLoadCredsModal = () => {
        if (loadCredsBackdrop) {
          loadCredsBackdrop.style.display = "none";
        }
        openLoadCredsFile();
      };
      if (loadCredsClose) loadCredsClose.addEventListener("click", hideLoadCredsModal);
      if (loadCredsContinue) loadCredsContinue.addEventListener("click", hideLoadCredsModal);
      if (loadCredsBackdrop) {
        loadCredsBackdrop.addEventListener("click", (e) => {
          if (e.target === loadCredsBackdrop) hideLoadCredsModal();
        });
      }
      loadCredsBtn.addEventListener("click", showLoadCredsModal);
      loadCredsFile.addEventListener("change", () => {
        if (loadCredsFile.files && loadCredsFile.files[0]) {
          doLoadCreds();
        }
      });
    }
    if (maxResultsBackdrop) {
      maxResultsBackdrop.addEventListener("click", hideMaxResultsModal);
    }
    function formatDate(value) {
      if (!value) return "";
      const normalized = normalizeDateString(value);
      if (normalized) return normalized;
      return value;
    }

    function pageUrlFor(release) {
      const url = release.url || "";
      if (!url) return "#";
      if (url.includes("/album/")) return url.split("/album/")[0];
      if (url.includes("/track/")) return url.split("/track/")[0];
      return url;
    }

    let scrapeStatus = { scraped: new Set(), notScraped: new Set() };

    function buildEmbedUrl(id, isTrack) {
      if (!id) return null;
      const kind = isTrack ? "track" : "album";
      return `https://bandcamp.com/EmbeddedPlayer/${kind}=${id}/size=large/bgcol=ffffff/linkcol=0687f5/tracklist=true/artwork=small/transparent=true/`;
    }

    async function ensureEmbed(release) {
      if (release.embed_url && release.description) {
        return release.embed_url;
      }
      if (!release.url || !embedProxyUrl) return null;

      const applyEmbedData = (data) => {
        if (!data) return null;
        const embedUrl = data.embed_url || buildEmbedUrl(data.release_id, data.is_track);
        if (embedUrl) release.embed_url = embedUrl;
        if (data.release_id) release.release_id = data.release_id;
        if (typeof data.is_track === "boolean") {
          release.is_track = data.is_track;
        }
        if (data.description) {
          release.description = data.description;
        }
        return embedUrl;
      };

      try {
        const response = await fetch(`${embedProxyUrl}?url=${encodeURIComponent(release.url)}`);
        if (!response.ok) throw new Error(`Proxy fetch failed: ${response.status}`);
        const data = await response.json();
        return applyEmbedData(data);
      } catch (err) {
        console.warn("Failed to fetch embed info", err);
        return null;
      }
    }

    function renderFilters(sourceList = releases) {
      const counts = sourceList.reduce((acc, r) => {
        if (!r.page_name) return acc;
        acc[r.page_name] = (acc[r.page_name] || 0) + 1;
        return acc;
      }, {});
      const labels = Object.keys(counts)
        .sort((a, b) => a.toLowerCase().localeCompare(b.toLowerCase()));
      const container = document.getElementById("label-filters");
      container.innerHTML = "";

      if (labels.length === 0) {
        container.innerHTML = "<div class='detail-meta'>No label/page data available.</div>";
        return;
      }

      const labelSignature = labels.join("||");
      if (state.showOnlyLabels.size === 0 && labelSignature !== lastLabelSignature) {
        state.showLabels = new Set(labels);
      } else if (state.showLabels.size === 0) {
        labels.forEach(label => state.showLabels.add(label));
      }
      lastLabelSignature = labelSignature;

      const showOnlyMode = state.showOnlyLabels.size > 0;

      labels.forEach(label => {
        const wrapper = document.createElement("div");
        wrapper.className = "filter-item";
        if (showOnlyMode) wrapper.classList.add("show-only-active");

        const showCheckbox = document.createElement("input");
        showCheckbox.type = "checkbox";
        showCheckbox.className = "filter-checkbox show";
        showCheckbox.dataset.filterRole = "show";
        showCheckbox.checked = state.showLabels.has(label);
        showCheckbox.disabled = showOnlyMode;
        showCheckbox.addEventListener("change", () => {
          if (showCheckbox.checked) {
            state.showLabels.add(label);
          } else {
            state.showLabels.delete(label);
          }
          renderTable();
        });

        const showOnlyCheckbox = document.createElement("input");
        showOnlyCheckbox.type = "checkbox";
        showOnlyCheckbox.className = "filter-checkbox show-only";
        showOnlyCheckbox.dataset.filterRole = "show-only";
        showOnlyCheckbox.checked = state.showOnlyLabels.has(label);
        showOnlyCheckbox.addEventListener("change", () => {
          if (showOnlyCheckbox.checked) {
            state.showOnlyLabels.add(label);
          } else {
            state.showOnlyLabels.delete(label);
          }
          syncShowCheckboxAvailability();
          renderTable();
        });

        const text = document.createElement("span");
        text.textContent = label;
        const count = document.createElement("span");
        count.className = "filter-count";
        count.textContent = `(${counts[label]})`;
        wrapper.appendChild(showCheckbox);
        wrapper.appendChild(showOnlyCheckbox);
        wrapper.appendChild(text);
        wrapper.appendChild(count);
        container.appendChild(wrapper);
      });

      syncShowCheckboxAvailability();
    }

    function updateSelectionStatusLog() {
      let fromVal = state.dateFilterFrom || "";
      let toVal = state.dateFilterTo || "";
      if (fromVal && !toVal) toVal = fromVal;
      if (toVal && !fromVal) fromVal = toVal;
      if (!fromVal || !toVal) return;

      let startDate = parseDateString(fromVal);
      let endDate = parseDateString(toVal);
      if (!startDate || !endDate) return;
      if (endDate < startDate) {
        [startDate, endDate] = [endDate, startDate];
        [fromVal, toVal] = [toVal, fromVal];
      }

      const msPerDay = 24 * 60 * 60 * 1000;
      const totalDays = Math.floor((endDate.getTime() - startDate.getTime()) / msPerDay) + 1;
      let populatedDays = 0;
      const cursor = new Date(startDate);
      while (cursor.getTime() <= endDate.getTime()) {
        const key = isoKeyFromDate(cursor);
        if (scrapeStatus.scraped.has(key)) populatedDays += 1;
        cursor.setDate(cursor.getDate() + 1);
      }

      const allPopulated = totalDays > 0 && populatedDays >= totalDays;
      if (populateLog) {
        let msg = allPopulated
        ? `Selected time period:\n\n${fromVal} to ${toVal}\n\nDate range fully populated. Displaying all releases in this date range.`
        : `Selected time period:\n\n${fromVal} to ${toVal}\n\n${totalDays-populatedDays} of ${totalDays} selected days not yet populated.\n\nClick "Populate release list" to populate all dates in the selected range.`; 

        populateLog.innerHTML = msg.replace(/\n/g, "<br>");
        populateLog.style.color = allPopulated ? "var(--muted)" : "#64a8ff";
        
        const rangeReleases = releases.filter(r => withinSelectedRange(r) && r.url);
        const hasPreloadableReleases = rangeReleases.some(r => !(r.embed_url && r.description));
        if (allPopulated && hasPreloadableReleases) {
          msg = `\n\n<span style="color:#64a8ff;">For faster browsing, "Star" the releases you're interested in to pre-load their Bandcamp player widgets, then filter using the "Starred" button at the top right.\n\nYou can also click 'Preload release data' to pre-fetch Bandcamp players for all releases in this date range.</span>`;
          populateLog.innerHTML += msg.replace(/\n/g, "<br>");
        }
      }

      if (populateBtn) {
        populateBtn.disabled = allPopulated;
        populateBtn.textContent = allPopulated ? "Release list populated" : "Populate release list";
        populateBtn.title = allPopulated ? "All dates in this range are already populated" : "";
      }
    }

    function updateStatusForDateFilter() {
      if (!populateLog) return;
      if (!state.filterByDate) {
        populateLog.textContent = "Showing all populated releases (only from previously downloaded date ranges).";
        populateLog.scrollTop = populateLog.scrollHeight;
        return;
      }
      updateSelectionStatusLog();
    }

    function updateHeaderRange(count = null) {
      const fromVal = state.dateFilterFrom || "";
      const toVal = state.dateFilterTo || "";
      const start = fromVal || toVal;
      const end = toVal || fromVal;
      if (headerRangeLabel) {
        if (!start && !end) {
          headerRangeLabel.textContent = "";
        } else if (start === end) {
          headerRangeLabel.textContent = `Date range: ${start}`;
        } else {
          headerRangeLabel.textContent = `Date range: ${start} to ${end}`;
        }
      }
      if (headerCountLabel) {
        const label = count == null ? "" : `${count} release${count === 1 ? "" : "s"} shown`;
        headerCountLabel.textContent = label;
      }
      const rangeReleases = releases.filter(r => withinSelectedRange(r) && r.url);
      const hasPendingPreload = rangeReleases.some(r => !(r.embed_url && r.description));
      const fromKey = state.dateFilterFrom || state.dateFilterTo || "";
      const toKey = state.dateFilterTo || state.dateFilterFrom || "";
      const hasScrapedRange = scrapeStatus && scrapeStatus.scraped
        ? (() => {
            const start = parseDateString(fromKey);
            const end = parseDateString(toKey || fromKey);
            if (!start || !end) return false;
            let cursor = new Date(start);
            const last = new Date(end);
            while (cursor <= last) {
              const key = isoKeyFromDate(cursor);
              if (!scrapeStatus.scraped.has(key)) return false;
              cursor.setDate(cursor.getDate() + 1);
            }
            return true;
          })()
        : false;
      if (preloadBtn) {
        const fullyPreloaded = hasScrapedRange && rangeReleases.length > 0 && !hasPendingPreload;
        const canPreload = hasScrapedRange && hasPendingPreload;
        if (fullyPreloaded) {
          preloadBtn.disabled = true;
          preloadBtn.textContent = "Release data preloaded";
          preloadBtn.title = "All embeds already cached for this range";
        } else if (canPreload) {
          preloadBtn.disabled = false;
          preloadBtn.textContent = "Preload release data";
          preloadBtn.title = "Fetch embed data for releases in this range";
        } else if (!hasScrapedRange){
          preloadBtn.disabled = true;
          preloadBtn.textContent = "Preload release data";
          preloadBtn.title = "Populate this range before preloading embeds";
        } else {
          preloadBtn.disabled = true;
          preloadBtn.textContent = "Preload release data";
          preloadBtn.title = "Preload unavailable";
        }
        preloadBtn.style.opacity = preloadBtn.disabled ? "0.6" : "1";
        preloadBtn.style.cursor = preloadBtn.disabled ? "not-allowed" : "pointer";
      }
    }

    function syncShowCheckboxAvailability() {
      const disableShow = state.showOnlyLabels.size > 0;
      document.querySelectorAll("#label-filters .filter-item").forEach(item => {
        const show = item.querySelector('input[data-filter-role="show"]');
        if (show) {
          show.disabled = disableShow;
        }
        item.classList.toggle("show-only-active", disableShow);
      });
    }

    function sortData(items) {
      const {sortKey, direction} = state;
      const dir = direction === "asc" ? 1 : -1;
      return items.slice().sort((a, b) => {
        if (sortKey === "date") {
          const da = normalizeDateString(a.date);
          const db = normalizeDateString(b.date);
          if (da === db) return 0;
          if (!da) return 1;
          if (!db) return -1;
          return da > db ? dir : -dir;
        }
        const av = (a[sortKey] || "").toLowerCase();
        const bv = (b[sortKey] || "").toLowerCase();
        if (av === bv) return 0;
        return av > bv ? dir : -dir;
      });
    }

    function closeOpenDetailRows() {
      document.querySelectorAll(".detail-row").forEach(node => {
        const iframe = node.querySelector("iframe");
        if (iframe) iframe.remove();
        node.remove();
      });
      document.querySelectorAll("tr.data-row").forEach(row => row.classList.remove("expanded"));
    }

    function createDetailRow(release) {
      const tr = document.createElement("tr");
      tr.className = "detail-row";
      const td = document.createElement("td");
      td.colSpan = 6;

      td.innerHTML = `
        <div class="detail-card">
          <div class="detail-body">
            <div class="embed-wrapper" data-embed-target>
              <div class="detail-meta">Loading player…</div>
            </div>
            <div class="detail-desc" data-desc-target>Loading description…</div>
          </div>
        </div>`;
      tr.appendChild(td);
      td.addEventListener("click", (evt) => {
        // Ignore clicks directly on the iframe
        if (evt.target.tagName.toLowerCase() === "iframe") return;
        // Focus the parent data row without toggling collapse
        const dataRow = tr.previousElementSibling;
        if (dataRow && dataRow.classList.contains("data-row")) {
          dataRow.focus();
        }
      });
      return tr;
    }

    function renderTable() {
      const tbody = document.getElementById("release-rows");
      tbody.innerHTML = "";
      closeOpenDetailRows();

      const dateFiltered = releases.filter(r => withinSelectedRange(r));
      renderFilters(dateFiltered);
      const filtered = dateFiltered.filter(r => {
        const key = releaseKey(r);
        const useShowOnly = state.showOnlyLabels.size > 0;
        const activeSet = useShowOnly ? state.showOnlyLabels : state.showLabels;
        if (activeSet.size > 0) {
          if (r.page_name && !activeSet.has(r.page_name)) return false;
        }
        if (state.showOnlyStarred) {
          if (!key || !state.starred.has(key)) return false;
        }

        if (state.hideViewed && state.hideViewedSnapshot.size > 0) {
          if (state.expandedKey && key === state.expandedKey) return true;
          return !state.hideViewedSnapshot.has(key);
        }
        return true;
      });

      const sorted = sortData(filtered);
      document.getElementById("empty-state").style.display = sorted.length ? "none" : "block";

      sorted.forEach(release => {
        const tr = document.createElement("tr");
        const key = releaseKey(release) || "";
        tr.className = "data-row";
        tr.dataset.key = key;
        tr.dataset.page = release.page_name || "";
        tr.tabIndex = 0;
        tr.innerHTML = `
          <td style="width:24px;"><span class="row-dot"></span></td>
          <td style="width:34px; text-align:center;">
            <button type="button" class="star-btn" data-star-btn aria-label="Star this release" aria-pressed="false" title="Star this release">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"></path>
              </svg>
            </button>
          </td>
          <td><a class="link" href="${pageUrlFor(release)}" target="_blank" rel="noopener">${release.page_name || "Unknown"}</a></td>
          <td><a class="link" href="${pageUrlFor(release)}" target="_blank" rel="noopener">${release.artist || "—"}</a></td>
          <td data-title-cell><a class="link" href="${release.url || "#"}" target="_blank" rel="noopener" data-title-link>${release.title || "—"}</a>${state.showCachedBadges && release.embed_url ? ' <span class="cached-badge">cached</span>' : ''}</td>
          <td>${formatDate(release.date)}</td>
        `;
        const existingRead = state.viewed.has(key);
        const initialDot = tr.querySelector(".row-dot");
        if (initialDot) initialDot.classList.toggle("read", existingRead);
        tr.classList.toggle("unseen", !existingRead);
        if (state.starred.has(key)) {
          tr.classList.add("starred");
        }
        const starBtn = tr.querySelector("[data-star-btn]");
        updateStarButton(starBtn, state.starred.has(key));
        if (starBtn) {
          starBtn.addEventListener("click", (evt) => {
            evt.stopPropagation();
            const next = !state.starred.has(key);
            setStarred(release, next, {row: tr, button: starBtn});
          });
        }
        if (state.starred.has(key)) {
          ensureEmbed(release).then(() => markCachedBadge(tr, release));
        }

        tr.addEventListener("click", (evt) => {
          if (evt.target && evt.target.matches("a[data-title-link]")) {
            // Allow middle/cmd click without toggling rows
            if (evt.metaKey || evt.ctrlKey || evt.button === 1) {
              return;
            }
            evt.preventDefault();
          }
          tr.focus();
          const existingDetail = tr.nextElementSibling;
          const hasDetail = existingDetail && existingDetail.classList.contains("detail-row");
          const wasVisible = hasDetail && existingDetail.style.display !== "none";

          // If already visible, toggle closed.
          if (wasVisible) {
            closeOpenDetailRows();
            state.expandedKey = null;
            return;
          }

          // Hide others
          closeOpenDetailRows();

          let detail = existingDetail;
          if (!hasDetail) {
            detail = createDetailRow(release);
            tr.after(detail);
          } else {
            // ensure adjacency and show
            tr.after(detail);
            detail.style.display = "";
          }
          tr.classList.add("expanded");
          state.expandedKey = key;

          const embedTarget = detail.querySelector("[data-embed-target]");
          const descTarget = detail.querySelector("[data-desc-target]");
          const dot = tr.querySelector(".row-dot");
          if (dot) dot.classList.add("read");
          tr.classList.remove("unseen");
          const cachedUrl = key;
          if (cachedUrl) {
            state.viewed.add(cachedUrl);
          }
          setViewed(release, true);
          if (descTarget) {
            descTarget.textContent = release.description || "Loading description…";
          }
          ensureEmbed(release).then(embedUrl => {
              if (!embedUrl) {
                embedTarget.innerHTML = `<div class="detail-meta">No embed available. Is the app still running? <br><a class="link" href="${release.url || "#"}" target="_blank" rel="noopener">Open on Bandcamp</a>.</div>`;
                return;
              }
            const height = release.is_track ? 320 : 480;
            embedTarget.innerHTML = `<iframe title="Bandcamp player" style="border:0; width:100%; height:${height}px;" src="${embedUrl}" seamless></iframe>`;
            markCachedBadge(tr, release);
            if (descTarget) {
              descTarget.textContent = release.description || "No description available.";
            }
          });
        });

        tr.addEventListener("keydown", (evt) => {
          if (evt.key === "Escape") {
            evt.preventDefault();
            closeOpenDetailRows();
            return;
          }
          if (evt.key === " " || evt.key === "Spacebar" || evt.key === "Space") {
            evt.preventDefault();
            tr.click();
            return;
          }
          if (evt.key === "Enter") {
            evt.preventDefault();
            tr.click();
            return;
          }
          if (evt.key === "ArrowDown" || evt.key === "ArrowUp") {
            evt.preventDefault();
            const rows = Array.from(document.querySelectorAll("tr.data-row"));
            const idx = rows.indexOf(tr);
            const nextIdx = evt.key === "ArrowDown" ? idx + 1 : idx - 1;
            if (nextIdx >= 0 && nextIdx < rows.length) {
              rows[nextIdx].focus();
            }
            return;
          }
          if (evt.key.toLowerCase() === "u") {
            evt.preventDefault();
            const markerCell = tr.querySelector("td:first-child");
            if (markerCell) {
              const dot = markerCell.querySelector(".row-dot");
              if (dot) dot.classList.toggle("read", false);
              else {
                const newDot = document.createElement("span");
                newDot.className = "row-dot";
                markerCell.appendChild(newDot);
              }
              setViewed(release, false);
            }
          }
          if (evt.key.toLowerCase() === "s") {
            evt.preventDefault();
            const next = !state.starred.has(key);
            const btn = tr.querySelector("[data-star-btn]");
            setStarred(release, next, {row: tr, button: btn});
          }
        });

        const markerCell = tr.querySelector("td:first-child");
        if (markerCell) {
          markerCell.addEventListener("click", (evt) => {
            evt.stopPropagation();
            const dot = markerCell.querySelector(".row-dot");
            if (dot) {
              const willBeRead = !dot.classList.contains("read");
              dot.classList.toggle("read");
              tr.classList.toggle("unseen", !willBeRead);
              setViewed(release, willBeRead);
            }
          });
        }

        // Hover/focus-based preload with debounce (0.2s)
        let preloadTimer;
        const schedulePreload = () => {
          preloadTimer = setTimeout(() => ensureEmbed(release), 200);
        };
        const cancelPreload = () => {
          if (preloadTimer) {
            clearTimeout(preloadTimer);
            preloadTimer = null;
          }
        };
        tr.addEventListener("mouseenter", schedulePreload);
        tr.addEventListener("mouseleave", cancelPreload);
        tr.addEventListener("focus", schedulePreload);
        tr.addEventListener("blur", cancelPreload);

        tbody.appendChild(tr);
      });
      refreshSortIndicators();
      updateHeaderRange(sorted.length);
    }

    function refreshSortIndicators() {
      document.querySelectorAll("th[data-sort]").forEach(th => {
        const indicator = th.querySelector(".sort-indicator");
        const key = th.dataset.sort;
        if (state.sortKey === key) {
          indicator.textContent = state.direction === "asc" ? "▲" : "▼";
          th.style.color = "var(--text)";
        } else {
          indicator.textContent = "";
          th.style.color = "var(--muted)";
        }
      });
    }

    function attachHeaderSorting() {
      document.querySelectorAll("th[data-sort]").forEach(th => {
        th.addEventListener("click", () => {
          const key = th.dataset.sort;
          if (state.sortKey === key) {
            state.direction = state.direction === "asc" ? "desc" : "asc";
          } else {
            state.sortKey = key;
            state.direction = key === "date" ? "desc" : "asc";
          }
          renderTable();
        });
      });
    }

    renderFilters();
    attachHeaderSorting();
    const settingsBackdrop = document.getElementById("settings-backdrop");
    const settingsBtn = document.getElementById("settings-btn");
    const settingsClose = document.getElementById("settings-close");
    const settingsReset = document.getElementById("settings-reset");
    const hideViewedBtn = document.getElementById("hide-viewed-btn");
    const showStarredBtn = document.getElementById("show-starred-btn");
    const markSeenBtn = document.getElementById("mark-seen");
    const markUnseenBtn = document.getElementById("mark-unseen");
    const dateFilterFrom = document.getElementById("date-filter-from");
    const dateFilterTo = document.getElementById("date-filter-to");
    const filterByDateToggle = document.getElementById("filter-by-date");
    const showCachedToggle = document.getElementById("show-cached-toggle");
    const scrapePanel = document.getElementById("scrape-wireframe");
    const scrapePanelBody = document.getElementById("scrape-wireframe-body");
    const sidebar = document.querySelector("aside");
    const calendarCard = document.getElementById("calendar-card");
    const backToTopBtn = document.getElementById("back-to-top");
    const calendarRange = document.getElementById("calendar-range");
    const calendarRangeMonth = document.getElementById("calendar-range-month");
    const populateBtn = document.getElementById("populate-range");
    const preloadBtn = document.getElementById("preload-range");
    const selectMonthBtn = document.getElementById("select-month-btn");
    const statusLogCard = document.querySelector(".calendar-log");
    const statusToggleBtn = document.getElementById("status-toggle");
    const CALENDAR_STATE_KEY = "bc_calendar_state_v1";
    // Reset load credentials button when settings panel is toggled
    const resetLoadCredsBtn = () => {
      if (loadCredsBtn) {
        loadCredsBtn.disabled = false;
        loadCredsBtn.textContent = "Load credentials";
      }
    };
    if (settingsBtn) settingsBtn.addEventListener("click", resetLoadCredsBtn);
    if (settingsClose) settingsClose.addEventListener("click", resetLoadCredsBtn);
    const headerRangeLabel = document.getElementById("header-range-label");
    const headerCountLabel = document.getElementById("header-count-label");
    const scrapeStatusUrl = apiRoot ? `${apiRoot}/scrape-status` : null;
    function normalizeDateString(value) {
      if (!value) return null;
      const match = String(value).match(/(\d{4})[-/](\d{2})[-/](\d{2})/);
      if (!match) return null;
      const [, y, m, d] = match;
      return `${y}-${m}-${d}`;
    }

    function toggleSettings(open) {
      if (!settingsBackdrop) return;
      settingsBackdrop.style.display = open ? "flex" : "none";
    }
    if (settingsBtn) settingsBtn.addEventListener("click", () => toggleSettings(true));
    if (settingsClose) settingsClose.addEventListener("click", () => toggleSettings(false));
    if (settingsBackdrop) settingsBackdrop.addEventListener("click", (e) => {
      if (e.target === settingsBackdrop) toggleSettings(false);
    });
    const showMissingTokenModal = () => {
      if (missingTokenBackdrop) {
        missingTokenBackdrop.style.display = "flex";
      }
    };
    const hideMissingTokenModal = () => {
      if (missingTokenBackdrop) {
        missingTokenBackdrop.style.display = "none";
      }
      toggleSettings(true);
    };
    if (missingTokenClose) missingTokenClose.addEventListener("click", hideMissingTokenModal);
    if (missingTokenContinue) missingTokenContinue.addEventListener("click", hideMissingTokenModal);
    if (missingTokenBackdrop) {
      missingTokenBackdrop.addEventListener("click", (e) => {
        if (e.target === missingTokenBackdrop) hideMissingTokenModal();
      });
    }
    if (missingToken) {
      showMissingTokenModal();
    }

    async function performReset() {
      const clearCache = true;
      const clearViewed = true;
      const clearStarred = true;
      let hadError = false;
      if (apiRoot) {
        try {
          const resp = await fetch(`${apiRoot}/reset-caches`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({clear_cache: clearCache, clear_viewed: clearViewed, clear_starred: clearStarred}),
          });
          if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        } catch (err) {
          console.warn("Failed to reset via API", err);
          hadError = true;
        }
      } else {
        hadError = true; // cannot clear disk cache without API
      }
      state.viewed = new Set();
      state.starred = new Set();
      releases.forEach(r => {
        delete r.embed_url;
        delete r.release_id;
        delete r.is_track;
      });
      renderTable();
      if (populateLog) {
        const msg = "Cache has been reset.";
        populateLog.textContent = msg;
      }
      toggleSettings(false);
      if (hadError && clearCache) {
        alert("Could not clear disk cache (proxy not reachable). Run the app/proxy and try again.");
      } else {
        window.location.reload();
      }
    }
    if (settingsReset) settingsReset.addEventListener("click", performReset);

    function refreshToggleButtons() {
      if (hideViewedBtn) {
        hideViewedBtn.classList.toggle("toggle-active", state.hideViewed);
        hideViewedBtn.setAttribute("aria-pressed", String(state.hideViewed));
        hideViewedBtn.title = state.hideViewed ? "Showing only unseen releases" : "Show all releases";
      }
      if (showStarredBtn) {
        showStarredBtn.classList.toggle("toggle-active", state.showOnlyStarred);
        showStarredBtn.setAttribute("aria-pressed", String(state.showOnlyStarred));
        showStarredBtn.title = state.showOnlyStarred ? "Showing only starred releases" : "Show all releases";
      }
    }

    function applyHideViewed(checked) {
      const expandedRow = document.querySelector("tr.data-row.expanded");
      if (expandedRow && expandedRow.dataset.key) {
        state.expandedKey = expandedRow.dataset.key;
      }
      state.hideViewed = checked;
      if (checked) {
        state.hideViewedSnapshot = new Set(state.viewed);
      } else {
        state.hideViewedSnapshot = new Set();
      }
      refreshToggleButtons();
      renderTable();
    }
    if (hideViewedBtn) {
      hideViewedBtn.addEventListener("click", () => applyHideViewed(!state.hideViewed));
    }
    if (showStarredBtn) {
      showStarredBtn.addEventListener("click", () => {
        state.showOnlyStarred = !state.showOnlyStarred;
        refreshToggleButtons();
        renderTable();
      });
    }

    function markVisibleRows(viewed) {
      const rows = Array.from(document.querySelectorAll("#release-rows tr.data-row"));
      rows.forEach(row => {
        const key = row.dataset.key;
        const release = key ? releaseMap.get(key) : null;
        if (!release) return;
        setViewed(release, viewed);
        const dot = row.querySelector(".row-dot");
        if (dot) {
          dot.classList.toggle("read", viewed);
        }
        row.classList.toggle("unseen", !viewed);
      });
      if (state.hideViewed) {
        state.hideViewedSnapshot = new Set(state.viewed);
      }
      renderTable();
      renderCalendar("range");
    }
    if (markSeenBtn) markSeenBtn.addEventListener("click", () => markVisibleRows(true));
    if (markUnseenBtn) markUnseenBtn.addEventListener("click", () => markVisibleRows(false));

    if (showCachedToggle) {
      const savedShowCached = localStorage.getItem(SHOW_CACHED_KEY);
      if (savedShowCached !== null) {
        state.showCachedBadges = savedShowCached === "true";
      }
      showCachedToggle.checked = state.showCachedBadges;
      showCachedToggle.addEventListener("change", () => {
        state.showCachedBadges = !!showCachedToggle.checked;
        localStorage.setItem(SHOW_CACHED_KEY, String(state.showCachedBadges));
        renderTable();
      });
    }

    const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
    const calendars = {
      range: { container: calendarRange, current: new Date(), startKey: null, endKey: null },
    };

    function isoKeyFromDate(dateObj) {
      if (!(dateObj instanceof Date) || isNaN(dateObj.getTime())) return "";
      const y = dateObj.getFullYear();
      const m = String(dateObj.getMonth() + 1).padStart(2, "0");
      const d = String(dateObj.getDate()).padStart(2, "0");
      return `${y}-${m}-${d}`;
    }

    function getLastSelectableDate() {
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      const lastSelectable = new Date(today);
      lastSelectable.setDate(today.getDate() - 1);
      return lastSelectable;
    }

    function parseDateString(value) {
      const normalized = normalizeDateString(value);
      if (!normalized) return null;
      const parts = normalized.split("-");
      if (parts.length !== 3) return null;
      const [y, m, d] = parts.map(Number);
      const parsed = new Date(y, m - 1, d);
      if (isNaN(parsed.getTime())) return null;
      if (parsed.getFullYear() !== y || parsed.getMonth() !== m - 1 || parsed.getDate() !== d) return null;
      return parsed;
    }

    function withinSelectedRange(release) {
      if (!state.filterByDate) return true;
      let fromVal = state.dateFilterFrom || "";
      let toVal = state.dateFilterTo || "";
      if (fromVal && !toVal) toVal = fromVal;
      if (toVal && !fromVal) fromVal = toVal;
      const rowDate = normalizeDateString(release.date);
      if (!rowDate) return true;
      if (fromVal) {
        const fromDate = normalizeDateString(fromVal);
        if (fromDate && rowDate < fromDate) return false;
      }
      if (toVal) {
        const toDate = normalizeDateString(toVal);
        if (toDate && rowDate > toDate) return false;
      }
      return true;
    }

    function renderCalendar(type) {
      const cal = calendars[type];
      if (!cal || !cal.container) return;
      const grid = cal.container;
      grid.innerHTML = "";

      const monthLabel = calendarRangeMonth;
      if (monthLabel) {
        const monthName = cal.current.toLocaleString("en-US", { month: "short", year: "numeric" });
        monthLabel.textContent = monthName;
      }

      WEEKDAYS.forEach(day => {
        const label = document.createElement("div");
        label.className = "calendar-weekday";
        label.textContent = day;
        grid.appendChild(label);
      });

      const monthStart = new Date(cal.current.getFullYear(), cal.current.getMonth(), 1);
      const startOffset = monthStart.getDay();
      const totalCells = 42; // 6 weeks
      const lastSelectable = getLastSelectableDate();
      const startSelectedDate = cal.startKey ? parseDateString(cal.startKey) : null;
      const endSelectedDate = cal.endKey ? parseDateString(cal.endKey) : null;

      for (let idx = 0; idx < totalCells; idx++) {
        const dayNumber = idx - startOffset + 1;
        const cellDate = new Date(cal.current.getFullYear(), cal.current.getMonth(), dayNumber);
        const isOtherMonth = cellDate.getMonth() !== cal.current.getMonth();
        const key = isoKeyFromDate(cellDate);
        const cell = document.createElement("div");
        cell.className = "calendar-day";
        let isDisabled = cellDate > lastSelectable;
        if (isOtherMonth) cell.classList.add("other-month");
        if (isDisabled) cell.classList.add("disabled");
        if (cal.startKey === key || cal.endKey === key) cell.classList.add("selected");
        if (startSelectedDate && endSelectedDate && cellDate >= startSelectedDate && cellDate <= endSelectedDate) {
          cell.classList.add("in-range");
        }
        cell.textContent = "";
        const dateLabel = document.createElement("span");
        dateLabel.className = "date-label";
        dateLabel.textContent = String(cellDate.getDate());
        const scraped = scrapeStatus.scraped.has(key);
        const hasUnseen = releases.some(rel => {
          const relDate = formatDate(rel.date);
          const relKey = releaseKey(rel);
          if (!relDate || relDate !== key) return false;
          return !state.viewed.has(relKey);
        });
        if (scraped) {
          cell.classList.add("unseen-day");
        }
        if (hasUnseen) {
          const dot = document.createElement("span");
          dot.className = "dot unseen";
          dot.style.background = "#ff5f5f";
          dot.style.borderColor = "rgba(0,0,0,0.25)";
          cell.appendChild(dateLabel);
          const dots = document.createElement("div");
          dots.className = "dot-strip";
          dots.appendChild(dot);
          cell.appendChild(dots);
        } else {
          cell.appendChild(dateLabel);
          const dots = document.createElement("div");
          dots.className = "dot-strip";
          cell.appendChild(dots);
        }

        cell.addEventListener("click", (evt) => {
          if (isDisabled) return;
          const clickedKey = key;
          if (evt.shiftKey) {
            const startKey = cal.startKey || cal.endKey;
            const endKey = cal.endKey || cal.startKey;
            const baseStart = startKey ? parseDateString(startKey) : null;
            const baseEnd = endKey ? parseDateString(endKey) : null;
            const clickedDate = parseDateString(clickedKey);
            if (baseStart && baseEnd && clickedDate) {
              const newStart = baseStart < baseEnd ? baseStart : baseEnd;
              const newEnd = baseStart < baseEnd ? baseEnd : baseStart;
              if (clickedDate < newStart) {
                cal.startKey = isoKeyFromDate(clickedDate);
                cal.endKey = isoKeyFromDate(newEnd);
              } else if (clickedDate > newEnd) {
                cal.startKey = isoKeyFromDate(newStart);
                cal.endKey = isoKeyFromDate(clickedDate);
              } else {
                // clicked inside range → collapse to single day
                cal.startKey = clickedKey;
                cal.endKey = null;
              }
            } else if (cal.startKey) {
              cal.endKey = clickedKey;
              const s = parseDateString(cal.startKey);
              const e = parseDateString(cal.endKey);
              if (s && e && e < s) {
                cal.endKey = cal.startKey;
                cal.startKey = clickedKey;
              }
            } else {
              cal.startKey = clickedKey;
              cal.endKey = null;
            }
          } else {
            cal.startKey = clickedKey;
            cal.endKey = null;
          }
          renderCalendar("range");
          applyCalendarFiltersFromSelection();
        });
        grid.appendChild(cell);
      }
    }

    function shiftCalendarMonth(type, delta) {
      const cal = calendars[type];
      if (!cal) return;
      const next = new Date(cal.current.getFullYear(), cal.current.getMonth() + delta, 1);
      const now = new Date();
      const maxMonth = new Date(now.getFullYear(), now.getMonth(), 1);
      cal.current = next > maxMonth ? maxMonth : next;
      renderCalendar(type);
    }

    function initializeCalendars() {
      const dateValues = releases
        .map(entry => parseDateString(entry.date))
        .filter(Boolean)
        .sort((a, b) => a - b);
      const today = new Date();
      if (dateValues.length) {
        calendars.range.current = new Date(dateValues[0].getFullYear(), dateValues[0].getMonth(), 1);
      } else {
        calendars.range.current = new Date(today.getFullYear(), today.getMonth(), 1);
      }
      syncCalendarsFromInputs();
      renderCalendar("range");
    }

    function syncCalendarsFromInputs() {
      const fromVal = dateFilterFrom ? dateFilterFrom.value.trim() : "";
      const toVal = dateFilterTo ? dateFilterTo.value.trim() : "";
      const parsedFrom = parseDateString(fromVal);
      const parsedTo = parseDateString(toVal);
      calendars.range.startKey = parsedFrom ? isoKeyFromDate(parsedFrom) : null;
      calendars.range.endKey = parsedTo ? isoKeyFromDate(parsedTo) : null;
      const target = parsedTo || parsedFrom;
      if (target) {
        calendars.range.current = new Date(target.getFullYear(), target.getMonth(), 1);
      }
    }

    document.querySelectorAll("[data-cal-nav]").forEach(btn => {
      btn.addEventListener("click", () => {
        const role = btn.getAttribute("data-cal-nav") || "";
        if (role.startsWith("range")) shiftCalendarMonth("range", role.endsWith("prev") ? -1 : 1);
      });
    });

    document.querySelectorAll("[data-cal-today]").forEach(btn => {
      btn.addEventListener("click", () => {
        const cal = calendars.range;
        if (!cal) return;
        const lastSelectable = getLastSelectableDate();
        const lastKey = isoKeyFromDate(lastSelectable);
        cal.current = new Date(lastSelectable.getFullYear(), lastSelectable.getMonth(), 1);
        if (!cal.startKey || (cal.startKey && cal.endKey)) {
          cal.startKey = lastKey;
          cal.endKey = null;
        } else {
          cal.endKey = lastKey;
        }
        renderCalendar("range");
        applyCalendarFiltersFromSelection();
      });
    });

    function selectVisibleMonthRange() {
      const cal = calendars.range;
      if (!cal) return;
      const current = cal.current || new Date();
      const lastSelectable = getLastSelectableDate();
      let year = current.getFullYear();
      let month = current.getMonth();
      let startDate = new Date(year, month, 1);
      if (lastSelectable < startDate) {
        year = lastSelectable.getFullYear();
        month = lastSelectable.getMonth();
        startDate = new Date(year, month, 1);
      }
      let endDate = new Date(year, month + 1, 0);
      if (lastSelectable.getFullYear() === year && lastSelectable.getMonth() === month && lastSelectable < endDate) {
        endDate = new Date(lastSelectable);
      }
      cal.startKey = isoKeyFromDate(startDate);
      cal.endKey = isoKeyFromDate(endDate);
      renderCalendar("range");
      applyCalendarFiltersFromSelection();
    }
    if (selectMonthBtn) {
      selectMonthBtn.addEventListener("click", selectVisibleMonthRange);
    }
    if (preloadBtn) {
      preloadBtn.addEventListener("click", preloadEmbedsForRange);
    }

    function populateRangeFromCalendars(triggerBtn = null) {
      checkServerAlive();
      applyCalendarFiltersFromSelection();
      let startVal = dateFilterFrom ? dateFilterFrom.value.trim() : "";
      let endVal = dateFilterTo ? dateFilterTo.value.trim() : "";
      if (startVal && !endVal) endVal = startVal;
      if (endVal && !startVal) startVal = endVal;
      if (!apiRoot || !startVal || !endVal) return;
      if (populateLog) populateLog.style.color = "";
      const btn = triggerBtn || populateBtn;
      const original = btn ? btn.textContent : "";
      if (btn) {
        btn.disabled = true;
        btn.textContent = "Populating…";
      }
          async function runPopulate() {
            if (!window.EventSource) {
              alert("Populate requires EventSource support. Please use a modern browser.");
              if (btn) {
                btn.disabled = false;
                btn.textContent = original || "Populate";
              }
              return;
            }
            if (populateLog) populateLog.textContent = "";
            const url = `${apiRoot}/populate-range-stream?start=${encodeURIComponent(startVal)}&end=${encodeURIComponent(endVal)}`;
            const es = new EventSource(url);
            const handleError = (ev) => {
              es.close();
              const msg = (ev && ev.data) ? String(ev.data) : "Populate failed (stream error)";
              const lower = msg.toLowerCase();
              if (!maxNoticeShown && lower.includes("maximum") && lower.includes("result")) {
                maxNoticeShown = true;
                showMaxResultsModal();
              }
              const current = populateLog ? populateLog.textContent : "";
              const next = current ? `${current}\n${msg}` : msg;
              if (populateLog) populateLog.textContent = next;
              if (populateLog) populateLog.scrollTop = populateLog.scrollHeight;
              alert(msg);
              if (btn) {
                btn.disabled = false;
                btn.textContent = original || "Populate";
              }
            };
            es.onmessage = (ev) => {
              if (!ev || !ev.data) return;
              if (!maxNoticeShown && ev.data.includes("Maximum results")) {
                maxNoticeShown = true;
                showMaxResultsModal();
                appendPopulateLogLine("Maximum number of results reached. Stopping download.");
              }
              const current = populateLog ? populateLog.textContent : "";
              const next = current ? `${current}\n${ev.data}` : ev.data;
              if (populateLog) {
                populateLog.textContent = next;
                populateLog.scrollTop = populateLog.scrollHeight;
              }
              if (String(ev.data || "").startsWith("ERROR:")) {
                handleError({ data: ev.data });
              }
            };
            es.addEventListener("error", handleError);
            es.addEventListener("done", () => {
              es.close();
              window.location.reload();
            });
          }
          runPopulate();
    }
    if (populateBtn) populateBtn.addEventListener("click", () => populateRangeFromCalendars(populateBtn));

    async function preloadEmbedsForRange() {
      if (!embedProxyUrl) {
        alert("Embed proxy not configured.");
        return;
      }
      checkServerAlive();
      applyCalendarFiltersFromSelection();
      const btn = preloadBtn;
      const original = btn ? btn.textContent : "";
      if (btn) {
        btn.disabled = true;
        btn.textContent = "Preloading…";
      }
      const candidates = releases
        .filter(r => withinSelectedRange(r))
        .filter(r => r.url)
        .filter(r => !(r.embed_url && r.description));
      const total = candidates.length;
      if (populateLog) {
        populateLog.style.color = "";
        populateLog.textContent = total
          ? `Preloading embeds for ${total} releases…`
          : "Nothing to preload for this range.";
        populateLog.scrollTop = populateLog.scrollHeight;
      }
      let success = 0;
      let failures = 0;
      for (let i = 0; i < candidates.length; i++) {
        const release = candidates[i];
        const label = `${release.title || release.url || "Release"}`;
        appendPopulateLogLine(`(${i + 1}/${total}) ${label}`);
        try {
          const embedUrl = await ensureEmbed(release);
          if (embedUrl) {
            success += 1;
          } else {
            failures += 1;
            appendPopulateLogLine(`    No embed found for ${label}`);
          }
        } catch (err) {
          failures += 1;
          appendPopulateLogLine(`    Error for ${label}: ${err}`);
        }
      }
      appendPopulateLogLine(`Preload complete. Cached: ${success}/${total}${failures ? `, failed: ${failures}` : ""}.`);
      if (btn) {
        btn.disabled = false;
        btn.textContent = original || "Preload release data";
      }
      renderTable();
    }

    function setDefaultDateFilters() {
      if ((dateFilterFrom && dateFilterFrom.value) || (dateFilterTo && dateFilterTo.value)) return;
      if (!releases.length) return;
      const dates = releases
        .map(entry => parseDateString(entry.date))
        .filter(Boolean)
        .sort((a, b) => a - b);
      if (!dates.length) return;
      const first = isoKeyFromDate(dates[0]);
      const last = isoKeyFromDate(dates[dates.length - 1]);
      if (dateFilterFrom && !dateFilterFrom.value) dateFilterFrom.value = first;
      if (dateFilterTo && !dateFilterTo.value) dateFilterTo.value = last;
      onDateFilterChange();
    }

    function applyCalendarFiltersFromSelection() {
      const cal = calendars.range;
      const fromKey = cal.startKey;
      const toKey = cal.endKey || "";
      if (dateFilterFrom && fromKey) {
        dateFilterFrom.value = fromKey;
      }
      if (dateFilterTo) {
        dateFilterTo.value = toKey;
      }
      onDateFilterChange();
      updateStatusForDateFilter();
    }

    async function fetchScrapeStatus() {
      if (!scrapeStatusUrl) return;
      try {
        const params = new URLSearchParams();
        const firstDate = releases[0]?.date;
        const lastDate = releases[releases.length - 1]?.date;
        if (firstDate) params.set("start", formatDate(firstDate));
        if (lastDate) params.set("end", formatDate(lastDate));
        const resp = await fetch(`${scrapeStatusUrl}?${params.toString()}`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        scrapeStatus.scraped = new Set(data.scraped || []);
        const notScraped = data.not_scraped || data["not_scraped"] || [];
        scrapeStatus.notScraped = new Set(notScraped || []);
        renderCalendar("range");
        updateStatusForDateFilter();
        updateHeaderRange();
      } catch (err) {
        console.warn("Failed to load scrape status", err);
      }
    }

    function loadCalendarState() {
      if (!dateFilterFrom || !dateFilterTo) return;
      try {
        const raw = localStorage.getItem(CALENDAR_STATE_KEY);
        if (!raw) return;
        const data = JSON.parse(raw);
        if (data && typeof data === "object") {
          if (typeof data.from === "string") dateFilterFrom.value = data.from;
          if (typeof data.to === "string") dateFilterTo.value = data.to;
        }
      } catch (err) {}
      onDateFilterChange();
    }

    function persistCalendarState() {
      if (!dateFilterFrom || !dateFilterTo) return;
      const payload = {
        from: (dateFilterFrom.value || "").trim(),
        to: (dateFilterTo.value || "").trim(),
      };
      try {
        localStorage.setItem(CALENDAR_STATE_KEY, JSON.stringify(payload));
      } catch (err) {}
    }

    if (scrapePanel && scrapePanelBody) {
      scrapePanelBody.hidden = !scrapePanel.open;
      scrapePanel.addEventListener("toggle", () => {
        scrapePanelBody.hidden = !scrapePanel.open;
      });
    }

    if (statusLogCard && statusToggleBtn) {
      statusLogCard.classList.remove("collapsed");
      statusToggleBtn.setAttribute("aria-expanded", "true");
      statusToggleBtn.addEventListener("click", () => {
        const isCollapsed = statusLogCard.classList.toggle("collapsed");
        statusToggleBtn.setAttribute("aria-expanded", String(!isCollapsed));
      });
    }

    if (backToTopBtn) {
      backToTopBtn.addEventListener("click", () => {
        if (sidebar && typeof sidebar.scrollTo === "function") {
          sidebar.scrollTo({ top: 0, behavior: "auto" });
        } else {
          window.scrollTo({ top: 0, behavior: "auto" });
        }
      });
    }

    if (sidebar && calendarCard && backToTopBtn) {
      const toggleBackToTop = (visible) => {
        backToTopBtn.classList.toggle("is-visible", !visible);
      };

      if ("IntersectionObserver" in window) {
        const observer = new IntersectionObserver(
          (entries) => {
            entries.forEach((entry) => toggleBackToTop(entry.isIntersecting));
          },
          { root: sidebar, threshold: 0.2 }
        );
        observer.observe(calendarCard);
      } else {
        const updateBackToTop = () => {
          const sidebarRect = sidebar.getBoundingClientRect();
          const cardRect = calendarCard.getBoundingClientRect();
          const visible = cardRect.bottom > sidebarRect.top && cardRect.top < sidebarRect.bottom;
          toggleBackToTop(visible);
        };
        sidebar.addEventListener("scroll", updateBackToTop);
        window.addEventListener("resize", updateBackToTop);
        updateBackToTop();
      }
    }

    function onDateFilterChange() {
      state.dateFilterFrom = dateFilterFrom ? dateFilterFrom.value.trim() : "";
      state.dateFilterTo = dateFilterTo ? dateFilterTo.value.trim() : "";
      syncCalendarsFromInputs();
      renderCalendar("range");
      updateStatusForDateFilter();
      updateHeaderRange();
      persistCalendarState();
      renderTable();
    }
    if (dateFilterFrom) dateFilterFrom.addEventListener("input", onDateFilterChange);
    if (dateFilterTo) dateFilterTo.addEventListener("input", onDateFilterChange);
    const updateDateFilterUi = () => {
      if (!scrapePanel) return;
      scrapePanel.classList.toggle("calendar-disabled", !state.filterByDate);
    };
    if (filterByDateToggle) {
      filterByDateToggle.checked = state.filterByDate;
      updateDateFilterUi();
      filterByDateToggle.addEventListener("change", () => {
        state.filterByDate = !!filterByDateToggle.checked;
        updateDateFilterUi();
        renderTable();
        updateStatusForDateFilter();
      });
    }

    initializeCalendars();
    loadCalendarState();
    setTimeout(() => checkServerAlive(), 500);
    setInterval(() => checkServerAlive(), 5000);

    // -------------------------------------------------------------------------
    // Provider configuration (IMAP/Gmail)
    const providerSelect = document.getElementById("provider-select");
    const gmailConfigPanel = document.getElementById("gmail-config-panel");
    const imapConfigPanel = document.getElementById("imap-config-panel");
    const imapHost = document.getElementById("imap-host");
    const imapPort = document.getElementById("imap-port");
    const imapUser = document.getElementById("imap-user");
    const imapPass = document.getElementById("imap-pass");
    const imapFolder = document.getElementById("imap-folder");
    const imapSsl = document.getElementById("imap-ssl");
    const imapSave = document.getElementById("imap-save");
    const imapStatus = document.getElementById("imap-status");

    function updateImapConfigVisibility() {
      if (!providerSelect) return;
      const isImap = providerSelect.value === "imap";
      if (imapConfigPanel) imapConfigPanel.style.display = isImap ? "block" : "none";
      if (gmailConfigPanel) gmailConfigPanel.style.display = isImap ? "none" : "block";
    }

    async function loadProviderConfig() {
      if (!apiRoot) return;
      try {
        const resp = await fetch(`${apiRoot}/provider-config`);
        if (!resp.ok) return;
        const config = await resp.json();
        if (providerSelect) {
          providerSelect.value = config.provider || "gmail";
        }
        if (config.imap_config) {
          if (imapHost) imapHost.value = config.imap_config.host || "";
          if (imapPort) imapPort.value = config.imap_config.port || 993;
          if (imapUser) imapUser.value = config.imap_config.username || "";
          if (imapFolder) imapFolder.value = config.imap_config.folder || "INBOX";
          if (imapSsl) imapSsl.value = (config.imap_config.use_ssl !== false) ? "ssl" : "none";
          if (imapPass && config.imap_config.has_password) {
            imapPass.placeholder = "••••••••";
          }
        }
        updateImapConfigVisibility();
      } catch (e) {
        console.warn("Could not load provider config:", e);
      }
    }

    async function saveProviderType() {
      if (!apiRoot) return;
      try {
        const payload = {
          provider: providerSelect ? providerSelect.value : "gmail"
        };
        await fetch(`${apiRoot}/provider-config`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
      } catch (e) {
        console.warn("Could not save provider type:", e);
      }
    }

    async function saveProviderConfig() {
      if (!apiRoot) return;
      try {
        const payload = {
          provider: providerSelect ? providerSelect.value : "gmail"
        };
        if (providerSelect && providerSelect.value === "imap") {
          payload.imap_config = {
            host: imapHost ? imapHost.value : "",
            port: imapPort ? parseInt(imapPort.value, 10) || 993 : 993,
            username: imapUser ? imapUser.value : "",
            password: imapPass ? imapPass.value : "",
            folder: imapFolder ? imapFolder.value : "INBOX",
            use_ssl: imapSsl ? (imapSsl.value === "ssl") : true
          };
        }
        const resp = await fetch(`${apiRoot}/provider-config`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        if (resp.ok) {
          if (imapStatus) {
            imapStatus.style.color = "var(--accent)";
            imapStatus.textContent = "Configuration saved.";
          }
        } else {
          if (imapStatus) {
            imapStatus.style.color = "#b83a3a";
            imapStatus.textContent = "Failed to save configuration.";
          }
        }
      } catch (e) {
        if (imapStatus) {
          imapStatus.style.color = "#b83a3a";
          imapStatus.textContent = "Error: " + e.message;
        }
      }
    }

    if (providerSelect) {
      providerSelect.addEventListener("change", () => {
        updateImapConfigVisibility();
        saveProviderType();
      });
    }
    if (imapSave) imapSave.addEventListener("click", saveProviderConfig);

    loadProviderConfig();

    async function initData() {
      try {
        setLoading("Loading releases…");
        await fetchReleases();
        const [viewed, starred] = await Promise.all([
          loadViewedSet(),
          loadStarredSet(),
        ]);
        state.viewed = viewed || new Set();
        state.starred = starred || new Set();
        setDefaultDateFilters();
        renderTable();
        renderCalendar("range");
        refreshToggleButtons();
        fetchScrapeStatus();
        hideLoading();
      } catch (err) {
        console.warn(err);
        showError((err && err.message) || "Failed to load releases. Is the bcfeed proxy running?");
      }
    }
    initData();
    })();
