console.log("Accessibility content script loaded");

// Keep state here
let scale = 1.0;  // 1.0 = 100%
let fontMode = "default"; // "default" | "opendyslexic"
let cbMode = "none"; // "none" | "protanopia" | "deuteranopia" | "tritanopia"

const STYLE_ID = "a11y-style";
const TEXT_SELECTORS = [
  "html", "body",
  "p", "span", "a", "li",
  "td", "th", "div", "section", "article",
  "input", "button", "textarea", "label",
  "h1","h2","h3","h4","h5","h6"
].join(", ");

function ensureStyleEl() {
  let styleEl = document.getElementById(STYLE_ID);
  if (!styleEl) {
    styleEl = document.createElement("style");
    styleEl.id = STYLE_ID;
    document.documentElement.appendChild(styleEl);
  }
  return styleEl;
}

function fontFamilyCSS() {
  if (fontMode === "opendyslexic") {
    // If you host the font, add @font-face in the same style tag or your own CSS.
    return `
      ${TEXT_SELECTORS} { font-family: 'OpenDyslexic', Arial, sans-serif !important; }
    `;
  } else {
    return `
      ${TEXT_SELECTORS} { font-family: inherit !important; }
    `;
  }
}

function colorBlindCSS() {
  // Simple approximations; replace later with precise SVG colormatrix if you want.
  switch (cbMode) {
    case "protanopia":
      return `html { filter: grayscale(50%) sepia(60%) !important; }`;
    case "deuteranopia":
      return `html { filter: grayscale(40%) sepia(50%) !important; }`;
    case "tritanopia":
      return `html { filter: grayscale(40%) hue-rotate(180deg) !important; }`;
    default:
      return `html { filter: none !important; }`;
  }
}

function scaleCSS() {
  // Two-pronged approach:
  // 1) Change root size so rem-based sites scale
  // 2) Force common text elements to a calc based on 1rem, overriding px with !important
  const pct = Math.round(scale * 100);
  return `
    html { font-size: ${pct}% !important; }
    ${TEXT_SELECTORS} { font-size: calc(${scale} * 1rem) !important; }
  `;
}

function renderCSS() {
  const styleEl = ensureStyleEl();
  styleEl.textContent = `
    /* A11y injected styles */
    ${scaleCSS()}
    ${fontFamilyCSS()}
    ${colorBlindCSS()}
  `;
}

function handleCommand(cmd) {
  switch (cmd) {
    case "increaseText":
      scale = Math.min(3.0, +(scale + 0.1).toFixed(2));
      renderCSS();
      break;

    case "decreaseText":
      scale = Math.max(0.5, +(scale - 0.1).toFixed(2));
      renderCSS();
      break;

    case "openDyslexic":
      fontMode = "opendyslexic";
      renderCSS();
      break;

    case "defaultFont":
      fontMode = "default";
      renderCSS();
      break;

    case "protanopia":
    case "deuteranopia":
    case "tritanopia":
      cbMode = cmd;
      renderCSS();
      break;

    case "resetFilters":
    case "":
      cbMode = "none";
      renderCSS();
      break;

    default:
      console.warn("Unknown command:", cmd);
  }
}

// Initial paint (in case you later persist settings)
renderCSS();

// Listen for popup messages
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  const cmd = request?.command ?? "";
  console.log("Received command:", cmd);
  handleCommand(cmd);
  sendResponse?.({ status: "ok" });
});
