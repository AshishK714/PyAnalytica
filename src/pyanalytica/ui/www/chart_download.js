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
 * container holds an image. Filenames come from the plot's id, e.g.
 * "two_variables_answer_plot.png", plus the chart's title when the server
 * provides one in the image's alt text.
 */
(function () {
  "use strict";

  var BUTTON_CLASS = "pa-chart-download";

  function fileName(container, img) {
    var base = (container.id || "chart").replace(/[^A-Za-z0-9]+/g, "_");
    var alt = (img && img.getAttribute("alt")) || "";
    if (alt && !/^plot/i.test(alt)) {
      base = alt.replace(/[^A-Za-z0-9]+/g, "_").replace(/^_+|_+$/g, "").slice(0, 60) || base;
    }
    return base + ".png";
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
