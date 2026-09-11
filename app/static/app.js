// Shared date/time internationalisation for TV-Trac.
//
// Loaded before each page's inline script so `formatDateLong` / `formatDate`
// are available globally and honour the selected locale (persisted in
// localStorage). The locale is chosen via a flag button that opens a small
// popover listing every format option.
(function () {
    "use strict";

    var STORAGE_KEY = "tvtrac_locale";

    // `mode: "custom"` reproduces the original built-in format; otherwise
    // `date` is an Intl locale and `hour12` toggles AM/PM.
    var PRESETS = {
        "default": { flag: "🏳️", name: "Default", sample: "Jun 14, 2026 · 14/06/2026", mode: "custom" },
        "en-US":   { flag: "🇺🇸", name: "US", sample: "Jun 14, 2026 · 06/14/2026", date: "en-US", hour12: true },
        "en-GB":   { flag: "🇬🇧", name: "UK", sample: "14 Jun 2026 · 14/06/2026", date: "en-GB", hour12: false },
        "iso":     { flag: "🌐", name: "ISO", sample: "2026-06-14 · 2026-06-14 14:30", date: null }
    };

    // Display order for the picker.
    var ORDER = ["default", "en-US", "en-GB", "iso"];

    // Only used by the "default" (legacy) preset.
    var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

    function currentLocale() {
        var key = localStorage.getItem(STORAGE_KEY) || "default";
        return PRESETS[key] ? key : "default";
    }

    function labelFor(key) {
        return PRESETS[key].name + " — " + PRESETS[key].sample;
    }

    function currentFlag() {
        return PRESETS[currentLocale()].flag;
    }

    function currentLabel() {
        return labelFor(currentLocale());
    }

    function setLocale(key) {
        if (!PRESETS[key]) key = "default";
        localStorage.setItem(STORAGE_KEY, key);
        return key;
    }

    function pad(n) {
        return String(n).padStart(2, "0");
    }

    // Parse a 'YYYY-MM-DD' string as UTC (avoids timezone shift).
    function parseDateOnly(value) {
        if (!value) return null;
        var p = String(value).split("-");
        if (p.length !== 3) return null;
        var y = parseInt(p[0], 10),
            m = parseInt(p[1], 10),
            d = parseInt(p[2], 10);
        if (isNaN(y) || isNaN(m) || isNaN(d)) return null;
        return new Date(Date.UTC(y, m - 1, d));
    }

    function parseDateTime(value) {
        if (!value) return null;
        var dt = new Date(value + (value.slice(-1) === "Z" ? "" : "Z"));
        return isNaN(dt.getTime()) ? null : dt;
    }

    // Air/release dates (date-only, e.g. "2026-06-14").
    function formatDateLong(value) {
        var dt = parseDateOnly(value);
        if (!dt) return value || "";
        var preset = PRESETS[currentLocale()];

        if (preset.mode === "custom") {
            return MONTHS[dt.getUTCMonth()] + " " + dt.getUTCDate() + ", " + dt.getUTCFullYear();
        }
        if (preset.date === null) {
            return dt.getUTCFullYear() + "-" + pad(dt.getUTCMonth() + 1) + "-" + pad(dt.getUTCDate());
        }
        return new Intl.DateTimeFormat(preset.date, {
            year: "numeric",
            month: "short",
            day: "numeric",
        }).format(dt);
    }

    // Watched timestamps (full datetime, e.g. "2026-06-14T14:30:00").
    function formatDate(value) {
        var dt = parseDateTime(value);
        if (!dt) return value || "";
        var preset = PRESETS[currentLocale()];

        if (preset.mode === "custom") {
            return (
                pad(dt.getDate()) + "/" + pad(dt.getMonth() + 1) + "/" + dt.getFullYear() +
                " " + pad(dt.getHours()) + ":" + pad(dt.getMinutes()) + ":" + pad(dt.getSeconds())
            );
        }
        if (preset.date === null) {
            return (
                dt.getFullYear() + "-" + pad(dt.getMonth() + 1) + "-" + pad(dt.getDate()) +
                " " + pad(dt.getHours()) + ":" + pad(dt.getMinutes()) + ":" + pad(dt.getSeconds())
            );
        }
        return new Intl.DateTimeFormat(preset.date, {
            year: "numeric",
            month: "2-digit",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
            hour12: preset.hour12,
        }).format(dt);
    }

    // ── Locale picker popover ────────────────────────────────────────────

    function ensureStyles() {
        if (document.getElementById("tvtrac-locale-styles")) return;
        var css =
            "#locale-picker{position:fixed;z-index:2000;background:var(--surface,#fff);border:1px solid var(--border,#e0e4e8);border-radius:8px;box-shadow:0 6px 20px rgba(0,0,0,0.15);padding:0.5rem;min-width:230px;}" +
            "#locale-picker .title{font-size:0.75rem;font-weight:600;color:var(--text-muted,#6b7280);padding:0.25rem 0.5rem 0.4rem;}" +
            "#locale-picker .option{display:flex;align-items:center;gap:0.5rem;width:100%;text-align:left;background:none;border:none;border-radius:6px;padding:0.4rem 0.5rem;font-size:0.8rem;color:var(--text,#1a1a2e);cursor:pointer;}" +
            "#locale-picker .option:hover{background:var(--border,#e0e4e8);}" +
            "#locale-picker .option.selected{background:rgba(233,69,96,0.12);}" +
            "#locale-picker .option .flag{font-size:1.1rem;}" +
            "#locale-picker .option .sample{margin-left:auto;color:var(--text-muted,#6b7280);font-size:0.7rem;white-space:nowrap;}";
        var style = document.createElement("style");
        style.id = "tvtrac-locale-styles";
        style.textContent = css;
        document.head.appendChild(style);
    }

    function closePicker() {
        var picker = document.getElementById("locale-picker");
        if (picker) picker.remove();
    }

    function openPicker(anchor, onSelect, ev) {
        if (ev) ev.stopPropagation();
        ensureStyles();

        // Toggle: if already open, close it.
        if (document.getElementById("locale-picker")) {
            closePicker();
            return;
        }

        var picker = document.createElement("div");
        picker.id = "locale-picker";

        var html = '<div class="title">Change date/time format</div>';
        for (var i = 0; i < ORDER.length; i++) {
            var key = ORDER[i];
            var p = PRESETS[key];
            var selected = key === currentLocale();
            html +=
                '<button type="button" class="option' + (selected ? " selected" : "") + '" data-key="' + key + '">' +
                '<span class="flag">' + p.flag + '</span>' +
                '<span class="name">' + p.name + '</span>' +
                '<span class="sample">' + p.sample + '</span>' +
                "</button>";
        }
        picker.innerHTML = html;
        document.body.appendChild(picker);

        // Position below the anchor, clamped to the viewport.
        var rect = anchor.getBoundingClientRect();
        var top = rect.bottom + 6;
        var left = rect.right - picker.offsetWidth;
        if (left < 8) left = 8;
        if (left + picker.offsetWidth > window.innerWidth - 8) {
            left = window.innerWidth - picker.offsetWidth - 8;
        }
        if (top + picker.offsetHeight > window.innerHeight - 8) {
            top = rect.top - picker.offsetHeight - 6;
        }
        if (top < 8) top = 8;
        picker.style.top = top + "px";
        picker.style.left = left + "px";

        picker.querySelectorAll(".option").forEach(function (btn) {
            btn.addEventListener("click", function (e) {
                e.stopPropagation();
                var key = btn.getAttribute("data-key");
                setLocale(key);
                anchor.textContent = PRESETS[key].flag;
                anchor.title = labelFor(key);
                closePicker();
                if (typeof onSelect === "function") onSelect(key);
            });
        });
    }

    // Close the picker when clicking outside it or pressing Escape.
    document.addEventListener("click", function (e) {
        var picker = document.getElementById("locale-picker");
        if (!picker) return;
        if (picker.contains(e.target)) return;
        closePicker();
    });
    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape") closePicker();
    });

    window.formatDateLong = formatDateLong;
    window.formatDate = formatDate;
    window.TVTracI18n = {
        openPicker: openPicker,
        currentFlag: currentFlag,
        currentLabel: currentLabel,
        getLocale: currentLocale,
    };
})();
