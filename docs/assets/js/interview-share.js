document.querySelectorAll('[data-copy-interviews]').forEach((button) => {
  button.addEventListener('click', async () => {
    const status = button.parentElement.querySelector('[role="status"]');
    try {
      await navigator.clipboard.writeText(button.dataset.copyInterviews);
      status.textContent = button.dataset.copied;
    } catch {
      status.textContent = button.dataset.fallback;
    }
  });
});
