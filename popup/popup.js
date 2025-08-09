function sendCommand(command) {
  console.log("Sending command:", command);
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (!tabs?.length) return;
    chrome.tabs.sendMessage(tabs[0].id, { command }, (response) => {
      if (chrome.runtime.lastError) {
        console.warn("tabs.sendMessage error:", chrome.runtime.lastError.message);
      } else {
        console.log("Content script response:", response);
      }
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  console.log("Popup loaded");

  // Text size
  document.getElementById("increaseText").addEventListener("click", () => {
    sendCommand("increaseText");
  });
  document.getElementById("decreaseText").addEventListener("click", () => {
    sendCommand("decreaseText");
  });

  // Font modes
  document.getElementById("openDyslexic").addEventListener("click", () => {
    sendCommand("openDyslexic");
  });
  document.getElementById("defaultFont").addEventListener("click", () => {
    sendCommand("defaultFont");
  });

  // Color blind mode
  document.getElementById("colorBlindSelect").addEventListener("change", (e) => {
    // Sends "", "protanopia", "deuteranopia", "tritanopia"
    sendCommand(e.target.value);
  });
});
