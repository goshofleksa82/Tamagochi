const state = {
  pet: null,
  savedPet: null,
  busy: false,
  mode: "loading",
};

const els = {
  petName: document.querySelector("#petName"),
  choicePanel: document.querySelector("#choicePanel"),
  saveSummary: document.querySelector("#saveSummary"),
  continueBtn: document.querySelector("#continueBtn"),
  newGameBtn: document.querySelector("#newGameBtn"),
  createPanel: document.querySelector("#createPanel"),
  gamePanel: document.querySelector("#gamePanel"),
  createForm: document.querySelector("#createForm"),
  nameInput: document.querySelector("#nameInput"),
  renameForm: document.querySelector("#renameForm"),
  renameInput: document.querySelector("#renameInput"),
  resetBtn: document.querySelector("#resetBtn"),
  petSprite: document.querySelector("#petSprite"),
  petMood: document.querySelector("#petMood"),
  petAge: document.querySelector("#petAge"),
  timeFactor: document.querySelector("#timeFactor"),
  endPanel: document.querySelector("#endPanel"),
  actionButtons: document.querySelectorAll("[data-action]"),
};

const stats = ["hunger", "happiness", "energy", "cleanliness"];

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Request failed.");
  }
  return data;
}

function formatAge(seconds) {
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${minutes % 60}m`;
}

function moodForPet(pet) {
  if (pet.isEnded) return "Game over";
  if (pet.status === "critical") return "Emergency care needed";
  if (pet.status === "needs-care") return "Needs attention";
  if (pet.happiness > 80 && pet.energy > 60) return "Thriving";
  return "Doing fine";
}

function applyDesign(pet) {
  const design = pet.design || {};
  const species = design.species || "cat";
  const pattern = design.pattern || "spots";

  els.petSprite.className = `pet-sprite ${pet.status} species-${species} pattern-${pattern}`;
  els.petSprite.style.setProperty("--pet-body", design.bodyColor || "#f5c46b");
  els.petSprite.style.setProperty("--pet-accent", design.accentColor || "#fff3cc");
}

function setBusy(isBusy) {
  state.busy = isBusy;
  document.querySelectorAll("button").forEach((button) => {
    button.disabled = isBusy || (button.dataset.action && state.pet && state.pet.isEnded);
  });
}

function render() {
  const pet = state.pet;
  const hasSave = Boolean(state.savedPet);
  els.choicePanel.classList.toggle("hidden", state.mode !== "choice" || !hasSave);
  els.createPanel.classList.toggle("hidden", state.mode !== "create");
  els.gamePanel.classList.toggle("hidden", state.mode !== "game" || !pet);
  els.resetBtn.classList.toggle("hidden", state.mode !== "game");

  if (state.mode === "choice" && hasSave) {
    els.petName.textContent = "Choose game";
    els.saveSummary.textContent = `Saved pet: ${state.savedPet.name}, age ${formatAge(state.savedPet.ageSeconds)}`;
    return;
  }

  if (state.mode === "create") {
    els.petName.textContent = "No pet yet";
    els.nameInput.focus();
    return;
  }

  if (!pet) return;

  els.petName.textContent = pet.name;
  els.renameInput.value = pet.name;
  els.petMood.textContent = moodForPet(pet);
  els.petAge.textContent = `Age ${formatAge(pet.ageSeconds)}`;
  els.timeFactor.textContent = `Stats change every ${pet.timeFactor.tickSeconds}s`;
  els.endPanel.classList.toggle("hidden", !pet.isEnded);
  els.actionButtons.forEach((button) => {
    button.disabled = state.busy || pet.isEnded;
  });
  applyDesign(pet);

  stats.forEach((stat) => {
    const value = pet[stat];
    document.querySelector(`#${stat}Value`).textContent = value;
    document.querySelector(`#${stat}Bar`).style.width = `${value}%`;
  });
}

async function loadPet() {
  const data = await api("/api/pet");
  state.savedPet = data.pet;
  if (state.mode === "game") {
    state.pet = data.pet;
  } else if (data.pet) {
    state.mode = "choice";
  } else {
    state.mode = "create";
  }
  render();
}

async function createPet(name) {
  setBusy(true);
  try {
    const data = await api("/api/pet", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
    state.pet = data.pet;
    state.savedPet = data.pet;
    state.mode = "game";
    render();
  } finally {
    setBusy(false);
  }
}

async function applyAction(action) {
  if (state.busy || !state.pet) return;
  setBusy(true);
  try {
    const data = await api("/api/action", {
      method: "POST",
      body: JSON.stringify({ action }),
    });
    state.pet = data.pet;
    state.savedPet = data.pet;
    render();
  } finally {
    setBusy(false);
  }
}

async function renamePet(name) {
  if (!state.pet) return;
  setBusy(true);
  try {
    const data = await api("/api/pet/name", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
    state.pet = data.pet;
    state.savedPet = data.pet;
    render();
  } finally {
    setBusy(false);
  }
}

els.createForm.addEventListener("submit", (event) => {
  event.preventDefault();
  createPet(els.nameInput.value);
});

els.continueBtn.addEventListener("click", () => {
  state.pet = state.savedPet;
  state.mode = "game";
  render();
});

els.newGameBtn.addEventListener("click", () => {
  state.pet = null;
  state.mode = "create";
  render();
});

els.renameForm.addEventListener("submit", (event) => {
  event.preventDefault();
  renamePet(els.renameInput.value);
});

els.resetBtn.addEventListener("click", () => {
  state.pet = null;
  state.mode = "create";
  render();
});

els.actionButtons.forEach((button) => {
  button.addEventListener("click", () => applyAction(button.dataset.action));
});

loadPet().catch((error) => {
  els.petName.textContent = error.message;
});

setInterval(() => {
  if (!state.busy && state.mode === "game") {
    loadPet().catch(() => {});
  }
}, 10000);
