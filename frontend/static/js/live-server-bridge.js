/**
 * VS Code / Cursor "Go Live" serves raw Jinja templates.
 * Send those files to the Flask app on port 5000.
 */
(function () {
  if (window.__EV_LIVE_BRIDGE) return;
  window.__EV_LIVE_BRIDGE = true;

  var html = (document.documentElement && document.documentElement.innerHTML) || "";
  var rawJinja = /{%\s*(extends|block|endblock)/.test(html);
  var file = (location.pathname.split("/").pop() || "").toLowerCase();
  var map = {
    "login.html": "/login",
    "register.html": "/register",
    "index.html": "/home",
    "dashboard.html": "/dashboard",
    "about.html": "/about",
    "dataset.html": "/dataset",
    "prediction.html": "/prediction",
    "comparison.html": "/comparison",
    "research.html": "/dataset#research",
    "xai.html": "/xai",
    "contact.html": "/contact",
    "admin.html": "/admin",
    "base.html": "/home",
    "live-index.html": "/login",
  };
  var fromTemplates =
    /\/templates\//i.test(location.pathname) ||
    /frontend\/templates/i.test(location.pathname);
  if (!rawJinja && !fromTemplates) return;

  var dest = map[file] || "/login";
  var flask = location.protocol + "//" + location.hostname + ":5000" + dest;

  function showHelp() {
    document.documentElement.innerHTML =
      '<body style="font-family:Segoe UI,sans-serif;background:#0b1220;color:#e5eefc;padding:48px;max-width:40rem">' +
      "<h1>Flask is not running</h1>" +
      "<p>Go Live opened a template file. This site needs the Python server.</p>" +
      "<p>In a terminal:</p>" +
      "<pre style=\"background:#111827;padding:12px;border-radius:8px\">python run.py</pre>" +
      '<p>Then open <a href="' +
      flask +
      '" style="color:#38bdf8">' +
      flask +
      "</a></p></body>";
  }

  fetch(location.protocol + "//" + location.hostname + ":5000/login", { method: "GET" })
    .then(function (res) {
      if (!res.ok) throw new Error("bad status");
      location.replace(flask);
    })
    .catch(showHelp);
})();
