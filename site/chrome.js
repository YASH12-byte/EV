(function () {
  const h = window.EVPages.href;
  const host = document.getElementById("navHost");
  if (!host) return;
  host.innerHTML = `
  <div class="bg-stage" aria-hidden="true"><div class="bg-aurora"></div><div class="bg-vignette"></div></div>
  <nav class="navbar navbar-expand-lg site-nav">
    <div class="container">
      <a class="navbar-brand brand" href="${h("/home")}">
        <span class="brand-mark"></span>
        <span>EV<span class="accent">Forecast</span></span>
      </a>
      <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navMain">
        <span class="navbar-toggler-icon"></span>
      </button>
      <div class="collapse navbar-collapse" id="navMain">
        <ul class="navbar-nav ms-auto align-items-lg-center gap-lg-1">
          <li class="nav-item"><a class="nav-link" href="${h("/home")}">Home</a></li>
          <li class="nav-item"><a class="nav-link" href="${h("/about")}">About</a></li>
          <li class="nav-item"><a class="nav-link" href="${h("/dataset")}">Dataset</a></li>
          <li class="nav-item"><a class="nav-link" href="${h("/prediction")}">Prediction</a></li>
          <li class="nav-item"><a class="nav-link" href="${h("/comparison")}">Models</a></li>
          <li class="nav-item"><a class="nav-link" href="${h("/contact")}">Contact</a></li>
          <li class="nav-item ms-lg-2" id="navAuth"></li>
        </ul>
      </div>
    </div>
  </nav>`;
  window.EVPages.bindLogout();
})();
