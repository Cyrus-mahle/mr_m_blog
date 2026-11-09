// Ask before dangerous actions. Kept in a file (not inline) so the
// Content Security Policy can stay strict.
document.addEventListener("submit", function (event) {
  var message = event.target.getAttribute("data-confirm");
  if (message && !window.confirm(message)) {
    event.preventDefault();
  }
});