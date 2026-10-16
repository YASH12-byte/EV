/**
 * VS Code Live Server cannot render Jinja. If a raw template is opened,
 * bounce to the matching static page on the same origin (port 5500).
 */
(function () {
  if (window.__EV_LIVE_BRIDGE) return;
  window.__EV_LIVE_BRIDGE = true;

  var html = (document.documentElement && document.documentElement.innerHTML) || "";
  var rawJinja = /{%\s*(extends|block|endblock)/.test(html);
  var fromTemplates =
    /\/templates\//i.test(location.pathname) ||
    /frontend\/templates/i.test(location.pathname);
  if (!rawJinja && !fromTemplates) return;

  var file = (location.pathname.split("/").pop() || "").toLowerCase();
  var staticMap = {
    "login.html": "/index.html",
    "register.html": "/register.html",
    "index.html": "/home.html",
    "dashboard.html": "/dashboard.html",
    "about.html": "/about.html",
    "dataset.html": "/dataset.html",
    "prediction.html": "/prediction.html",
    "comparison.html": "/comparison.html",
    "research.html": "/dataset.html",
    "xai.html": "/xai.html",
    "contact.html": "/contact.html",
    "admin.html": "/dashboard.html",
    "base.html": "/home.html",
    "live-index.html": "/index.html",
  };
  var dest = staticMap[file] || "/index.html";
  location.replace(location.protocol + "//" + location.host + dest);
})();
