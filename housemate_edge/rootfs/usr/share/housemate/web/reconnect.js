// Housemate: when the add-on restarts under an open panel, the editor shows
// "Cannot reconnect. Please reload the window." and waits for a click. This
// reloads the page by itself once the add-on answers again after being away for ten seconds or more, so that the agent
// reopens on its own (the launcher extension does that on load).
(function () {
  var failures = 0;
  function check() {
    fetch("healthz", { cache: "no-store", credentials: "same-origin" })
      .then(function (r) {
        if (!r.ok) throw new Error("not ready");
        if (failures >= 4) { location.reload(); return; }
        failures = 0;
      })
      .catch(function () { failures += 1; });
  }
  setInterval(check, 3000);
})();
