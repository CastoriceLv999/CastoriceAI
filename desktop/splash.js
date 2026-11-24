window.startup.onStatus(({ message, reduceMotion }) => {
  document.getElementById('status').textContent = message;
  document.body.classList.toggle('reduce-motion', reduceMotion);
});
