export function triggerDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename || "download";
  document.body.appendChild(a);
  a.click();
  a.remove();
  // Some browsers may cancel the download if the object URL is revoked immediately.
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
