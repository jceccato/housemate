// Housemate: a link that names a chat. A notification opens
//   /app/<add-on slug>/<chat id>
// Home Assistant's frontend gives the panel's page (this one, in an iframe) the part
// after the slug as its route, once the page asks to be told ("subscribe-properties"),
// and again whenever the route changes. When that route names a chat, say so to the
// add-on, which tells the editor to bring that chat's tab to the front. The page itself
// is the same either way: nothing here changes what the person sees.
(function () {
  if (window.parent === window) return;
  // Next to this script: the panel's own prefix, wherever Ingress put it.
  var open = document.currentScript.src.replace("deeplink.js", "open");
  var last = null;
  function onRoute(route) {
    var m = route && typeof route.path === "string" && route.path.match(/\/(ses_[A-Za-z0-9]+)\/?$/);
    var id = m ? m[1] : null;
    if (id === last) return;
    last = id;
    if (id) {
      fetch(open + "?session=" + encodeURIComponent(id), { method: "POST", credentials: "same-origin" })
        .catch(function () { /* the editor opens its usual chat instead */ });
    }
  }
  window.addEventListener("message", function (e) {
    if (e.source !== window.parent) return;
    var d = e.data;
    if (d && d.type === "home-assistant/properties") onRoute(d.route);
  });
  window.parent.postMessage({ type: "home-assistant/subscribe-properties" }, "*");
})();
