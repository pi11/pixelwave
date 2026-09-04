document.querySelectorAll("[data-channel-vote]").forEach((button) => {
  button.addEventListener("click", async () => {
    const rating = button.closest(".channel-rating");
    const value = Number(button.dataset.channelVote);
    const response = await fetch(`/api/radios/${rating.dataset.radioId}/vote?value=${value}`, {method: "POST"});
    if (!response.ok) {
      rating.dataset.error = "Vote failed";
      return;
    }
    delete rating.dataset.error;
    const result = await response.json();
    const buttons = rating.querySelectorAll("[data-channel-vote]");
    buttons[0].querySelector("span").textContent = result.likes;
    buttons[1].querySelector("span").textContent = result.dislikes;
    rating.querySelector(":scope > span strong").textContent = result.rating.toFixed(3);
    buttons[0].classList.toggle("selected", result.vote === 1);
    buttons[1].classList.toggle("selected", result.vote === -1);
  });
});
