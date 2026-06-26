import { useEffect, useState } from "react";
import { motion } from "framer-motion";

export function AnimatedCounter({ value, duration = 1.5, decimals = 0, suffix = "", prefix = "" }) {
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    if (value === undefined || value === null) return;
    const start = performance.now();
    const from = display;
    const to = Number(value);
    if (from === to) return;

    const animate = (now) => {
      const elapsed = (now - start) / 1000;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(from + (to - from) * eased);
      if (progress < 1) requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  }, [value, duration]);

  return (
    <motion.span
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      {prefix}{display.toFixed(decimals)}{suffix}
    </motion.span>
  );
}
