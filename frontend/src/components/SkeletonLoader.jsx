import { motion } from "framer-motion";

export function SkeletonCard({ height = 120 }) {
  return (
    <div className="skeleton-card" style={{ height }}>
      <motion.div
        className="skeleton-shimmer"
        animate={{ x: ["-100%", "100%"] }}
        transition={{ repeat: Infinity, duration: 1.5, ease: "easeInOut" }}
      />
    </div>
  );
}

export function SkeletonList({ count = 3, height = 80 }) {
  return (
    <div className="skeleton-list">
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} height={height} />
      ))}
    </div>
  );
}
