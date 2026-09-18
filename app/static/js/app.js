(() => {
  "use strict";

  const button = document.querySelector('[data-action="create-placeholder"]');
  if (button) {
    button.addEventListener("click", () => {
      button.textContent = "Stream creation arrives next";
      button.disabled = true;
    });
  }
})();

