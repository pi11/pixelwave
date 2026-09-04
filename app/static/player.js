const audio = new Audio();
audio.volume = .8;
let radio = null;
let currentTrack = null;
const $ = (id) => document.getElementById(id);

async function loadTrack(autoplay = true) {
  if (!radio) return;
  $("track-name").textContent = "Tuning…";
  try {
    const response = await fetch(`/api/radios/${radio}/next`);
    if (!response.ok) throw new Error((await response.json()).detail || "Station unavailable");
    const track = await response.json();
    currentTrack = track;
    audio.src = track.audio;
    $("track-name").textContent = track.name;
    $("artist").textContent = track.artist;
    $("artist").href = track.share_url || (track.provider === "audius" ? "https://audius.co" : "https://www.jamendo.com");
    $("cover").src = track.image;
    $("license").href = track.license_url || "https://creativecommons.org";
    $("like").querySelector("span").textContent = track.likes;
    $("dislike").querySelector("span").textContent = track.dislikes;
    $("like").classList.remove("selected");
    $("dislike").classList.remove("selected");
    if (autoplay) await audio.play();
  } catch (error) {
    $("track-name").textContent = error.message;
  }
}

document.querySelectorAll(".station").forEach((button) => button.addEventListener("click", async () => {
  document.querySelectorAll(".station").forEach(x => x.classList.remove("active"));
  button.classList.add("active");
  radio = button.dataset.radio;
  $("station-name").textContent = button.dataset.name;
  $("player").hidden = false;
  await loadTrack();
}));
$("toggle").addEventListener("click", () => audio.paused ? audio.play() : audio.pause());
$("next").addEventListener("click", () => loadTrack());
async function vote(value) {
  if (!currentTrack) return;
  const response = await fetch(`/api/tracks/${currentTrack.id}/vote`, {
    method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({value})
  });
  if (!response.ok) return;
  const result = await response.json();
  $("like").querySelector("span").textContent = result.likes;
  $("dislike").querySelector("span").textContent = result.dislikes;
  $("like").classList.toggle("selected", result.vote === 1);
  $("dislike").classList.toggle("selected", result.vote === -1);
}
$("like").addEventListener("click", () => vote(1));
$("dislike").addEventListener("click", () => vote(-1));
$("volume").addEventListener("input", (event) => audio.volume = event.target.value);
audio.addEventListener("play", () => $("toggle").textContent = "Ⅱ");
audio.addEventListener("pause", () => $("toggle").textContent = "▶");
audio.addEventListener("ended", () => loadTrack());
