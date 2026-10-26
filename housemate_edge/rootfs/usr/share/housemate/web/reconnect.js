// Housemate: when the add-on restarts under an open panel, the editor shows
// "Cannot reconnect. Please reload the window." and waits for a click. This
// reloads the page by itself once it sees the add-on has started afresh, so
// that the agent reopens on its own (the launcher extension does that on load).
//
// "Started afresh" is a different boot id: a file written at every start of the
// container and served beside this script. A blip in the network, or Home
// Assistant being away for a moment, leaves the id as it was and reloads nothing.
(function () {
  // Next to this script: the panel's own prefix, wherever Ingress put it.
  var boot = document.currentScript.src.replace("reconnect.js", "boot");
  var seen = null;
  function check() {
    fetch(boot, { cache: "no-store", credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.text() : Promise.reject(new Error("not ready")); })
      .then(function (id) {
        id = id.trim();
        if (seen === null) { seen = id; } else if (id !== seen) { location.reload(); }
      })
      .catch(function () { /* away for now: try again */ });
  }
  check();
  setInterval(check, 2000);
})();
