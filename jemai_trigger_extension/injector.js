function scanForJemaiTriggers() {
    const bodyText = document.body.innerText || "";
    const re = /(jemai::run::.+)|(jemai::exec::.+)|(jemai::list::.+)/ig;
    let found = bodyText.match(re);
    if (found) {
        for (const cmd of found) {
            let clean = cmd.replace(/^jemai::(run|exec|list)::/i, "").trim();
            fetch("http://localhost:32145/trigger", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({cmd: clean})
            }).then(() => console.log("[JEMAI EXT] Sent trigger:", clean))
              .catch(e => console.error("[JEMAI EXT] Send error:", e));
        }
    }
    // Heartbeat every scan
    fetch("http://localhost:32145/heartbeat", {method: "POST"})
      .then(() => console.log("[JEMAI EXT] Heartbeat sent"))
      .catch(e => console.error("[JEMAI EXT] Heartbeat error:", e));
}
setInterval(scanForJemaiTriggers, 2000);
