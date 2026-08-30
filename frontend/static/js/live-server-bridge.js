/**
 * If a raw Jinja template is opened outside Flask, silently send the
 * browser to the matching Flask route. No on-page notice is shown.
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
    "research.html": "/dataset",
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
  location.replace(location.protocol + "//" + location.hostname + ":5000" + dest);
})();
