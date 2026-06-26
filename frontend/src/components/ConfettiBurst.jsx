import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

const COLORS = ["#c74634", "#2d6a4f", "#f59e0b", "#3b82f6", "#8b5cf6", "#ec4899", "#14b8a6"];
const PARTICLES = 30;

function Particle({ color, angle, distance, delay, size }) {
  const x = Math.cos(angle) * distance * (0.6 + Math.random() * 0.4);
  const y = Math.sin(angle) * distance * (0.6 + Math.random() * 0.4);
  const rotate = Math.random() * 720 - 360;
  return (
    <motion.div
      className="confetti-particle"
      style={{ background: color, width: size, height: size, borderRadius: Math.random() > 0.5 ? "50%" : "2px" }}
      initial={{ x: 0, y: 0, opacity: 1, scale: 1, rotate: 0 }}
      animate={{ x, y, opacity: 0, scale: 0.3, rotate }}
      transition={{ duration: 0.6 + Math.random() * 0.6, delay, ease: [0.25, 0.46, 0.45, 0.94] }}
    />
  );
}

export function ConfettiBurst({ active = false }) {
  const [particles] = useState(() =>
    Array.from({ length: PARTICLES }, (_, i) => ({
      id: i,
      color: COLORS[i % COLORS.length],
      angle: (Math.PI * 2 * i) / PARTICLES + (Math.random() - 0.5) * 0.3,
      distance: 50 + Math.random() * 120,
      delay: Math.random() * 0.15,
      size: 4 + Math.random() * 6,
    }))
  );

  return (
    <AnimatePresence>
      {active && (
        <motion.div
          className="confetti-container"
          initial={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.5 }}
        >
          {particles.map((p) => (
            <Particle key={p.id} {...p} />
          ))}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
