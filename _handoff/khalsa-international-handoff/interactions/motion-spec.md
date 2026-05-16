# Motion Spec

## Durations
| Token | Value | Use |
|---|---|---|
| `motion.fast` | 120 ms | Hover, focus, small state changes |
| `motion.base` | 200 ms | Modals, page transitions, drawer |
| `motion.slow` | 320 ms | Hero reveals, large entrance |

## Easings
| Token | cubic-bezier | Use |
|---|---|---|
| `motion.standard` | `(0.4, 0, 0.2, 1)` | Default |
| `motion.decelerate` | `(0, 0, 0.2, 1)` | Entering elements |
| `motion.accelerate` | `(0.4, 0, 1, 1)` | Exiting elements |

## Patterns

**Hover** — backgrounds shift one step (e.g. blue → blue/90), 120ms ease standard.

**Focus** — `outline: 2px solid var(--color-royal-gold)` with 2px offset; never animate the outline itself.

**Page transition (web)** — `opacity 0→1` + `translateY(8px → 0)`, 200ms decelerate. No horizontal slides.

**Modal** — backdrop `opacity 0→1`, sheet `scale(0.96 → 1)` + `opacity`, 200ms decelerate. Exit reverses.

**Toast** — slide in from top-right, 200ms decelerate; auto-dismiss 4 s; exit 200ms accelerate.

**Mobile push transitions** — RN default platform.

**Reduced motion** — wrap every animation in `@media (prefers-reduced-motion: reduce)` and disable transforms/opacity transitions; instant changes only.
