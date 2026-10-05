/*
 * A "Download PNG" button on every chart.
 *
 * Learners put charts into reports written outside the app (a Word template,
 * slides), and the only way out was right-click > Save image as, which most
 * did not know existed. Every chart in the app is a Shiny plot output whose
 * <img> already holds the rendered PNG, so one script covers every panel,
 * including ones added later, and saves exactly the picture on screen.
 *
 * The button is added once per plot container and enabled only while the
 * container holds an image. The file is named for what the chart shows: the
 * panel, the columns chosen in it, and which chart of the panel it is, e.g.
 * "two_variables_charges_region_smoker_answer.png". Named by the plot's id
 * alone, every chart from a panel was "two_variables_answer_plot.png", and a
 * learner saving one per question got (1), (2), (3) ... and no way to tell
 * them apart.
 */
(function () {
  "use strict";

  var BUTTON_CLASS = "pa-chart-download";

  // Choices that say nothing about the chart: empty, "(none)", the defaults
  // of the "treat as" selects.
  var SKIP = { "": 1, "auto": 1, "none": 1, "(none)": 1 };

  function visible(el) {
    var box = el.closest(".shiny-input-container") || el;
    return box.offsetParent !== null;
  }

  // The values of the select boxes in the plot's own panel, in screen order.
  // Shiny names inputs "<panel>-<input>" and outputs "<panel>-<output>".
  function chosen(prefix) {
    var values = [];
    document.querySelectorAll('select[id^="' + prefix + '-"]').forEach(function (sel) {
      // The panel's own inputs only: "<panel>-<input>". A component inside it
      // (the decimals control is "<panel>-dec-...") says nothing about the chart.
      if (sel.id.slice(prefix.length + 1).indexOf("-") >= 0) return;
      if (!visible(sel)) return;
      Array.prototype.forEach.call(sel.selectedOptions || [], function (opt) {
        var v = String(opt.value || "").trim();
        if (!SKIP[v.toLowerCase()] && values.indexOf(v) < 0) values.push(v);
      });
    });
    return values;
  }

  function clean(text) {
    return String(text).replace(/[^A-Za-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
  }

  function fileName(container, img) {
    var id = container.id || "chart";
    var cut = id.indexOf("-");
    var prefix = cut > 0 ? id.slice(0, cut) : "";
    var which = (cut > 0 ? id.slice(cut + 1) : id).replace(/_?plot$/i, "");
    var parts = [prefix].concat(prefix ? chosen(prefix) : [], [which]);
    var base = parts.map(clean).filter(Boolean).join("_").slice(0, 100);
    return (base || "chart") + ".png";
  }

  function currentImage(container) {
    var img = container.querySelector("img");
    if (!img || !img.src || img.src.indexOf("data:image") !== 0) return null;
    return img;
  }

  function sync(container) {
    var button = container.querySelector(":scope > ." + BUTTON_CLASS);
    if (!button) {
      button = document.createElement("button");
      button.type = "button";
      button.className = BUTTON_CLASS + " btn btn-sm btn-light";
      button.textContent = "Download PNG";
      button.setAttribute("aria-label", "Download this chart as a PNG image");
      button.title = "Save this chart as an image, to put in a report or slides";
      button.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();
        var img = currentImage(container);
        if (!img) return;
        var link = document.createElement("a");
        link.href = img.src;
        link.download = fileName(container, img);
        document.body.appendChild(link);
        link.click();
        link.remove();
      });
      if (getComputedStyle(container).position === "static") {
        container.style.position = "relative";
      }
      container.appendChild(button);
    }
    var has = !!currentImage(container);
    button.disabled = !has;
    button.style.display = has ? "" : "none";
  }

  function syncAll() {
    document.querySelectorAll(".shiny-plot-output").forEach(sync);
  }

  // Charts arrive and change after every press of a panel's button, and
  // whole panels are rendered later (sections, modals), so watch the page.
  var pending = false;
  var observer = new MutationObserver(function () {
    if (pending) return;
    pending = true;
    window.requestAnimationFrame(function () {
      pending = false;
      syncAll();
    });
  });

  function start() {
    syncAll();
    observer.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ["src"] });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
