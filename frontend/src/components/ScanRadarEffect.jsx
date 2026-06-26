import { motion } from "framer-motion";

export function ScanRadarEffect({ active = false }) {
  if (!active) return null;

  return (
    <div className="radar-container">
      <motion.div
        className="radar-sweep"
        animate={{ rotate: [0, 360] }}
        transition={{ repeat: Infinity, duration: 2, ease: "linear" }}
      />
      {[1, 2, 3, 4].map((i) => (
        <motion.div
          key={i}
          className="radar-ring"
          style={{ animationDelay: `${i * 0.4}s` }}
          animate={{ scale: [1, 2.5], opacity: [0.6, 0] }}
          transition={{ repeat: Infinity, duration: 2.4, delay: i * 0.4, ease: "easeOut" }}
        />
      ))}
      <motion.div
        className="radar-dot"
        animate={{ scale: [0.8, 1.4, 0.8], opacity: [0.7, 1, 0.7] }}
        transition={{ repeat: Infinity, duration: 1.2, ease: "easeInOut" }}
      />
      <motion.div
        className="radar-glow"
        animate={{ scale: [1, 1.1, 1], opacity: [0.15, 0.25, 0.15] }}
        transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
      />
    </div>
  );
}
