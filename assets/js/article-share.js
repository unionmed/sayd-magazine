document.querySelectorAll(".article-share").forEach((bar) => {
  const url = document.querySelector('link[rel="canonical"]')?.href || location.href;
  const title = document.querySelector('meta[property="og:title"]')?.content || document.title;
  const share = bar.querySelector("[data-share-native]");
  const status = bar.querySelector(".article-share-status");

  share?.addEventListener("click", async () => {
    if (navigator.share) {
      try {
        await navigator.share({ title, url });
        return;
      } catch (error) {
        if (error.name === "AbortError") return;
      }
    }
    try {
      await navigator.clipboard.writeText(url);
      status.textContent = bar.dataset.copied;
      window.setTimeout(() => { status.textContent = ""; }, 3000);
    } catch {
      window.prompt(share.getAttribute("aria-label"), url);
    }
  });
});
