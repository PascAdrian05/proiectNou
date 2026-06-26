export function formatDistanceToNow(dateInput) {
  if (!dateInput) return "necunoscut";
  const date = typeof dateInput === "string" ? new Date(dateInput) : dateInput;
  if (Number.isNaN(date.getTime())) return "necunoscut";

  const deltaMs = Date.now() - date.getTime();
  const seconds = Math.floor(deltaMs / 1000);

  if (seconds < 60) return "acum";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `acum ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `acum ${hours}h`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `acum ${days} zile`;
  const weeks = Math.floor(days / 7);
  if (weeks < 5) return `acum ${weeks} sapt`;
  return date.toLocaleDateString("ro-RO");
}

export function classNames(...classes) {
  return classes.filter(Boolean).join(" ");
}
