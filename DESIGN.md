# DESIGN.md — YOLOv8 Security Monitor

> 监狱智能行为分析系统 design system. A real-time prison surveillance
> dashboard with dual-theme support: a light mode for the admin panels
> and a dark-only mode for the monitoring wall and login screen.

---

name: yolov8-security-monitor
description: >-
  Enterprise surveillance dashboard with light/dark dual theme,
  camera grid layout, real-time alert sidebar, and immersive
  dark-mode login. Chinese-first UI with monospace data displays.

tokens:

  color:
    light:
      bg: "#f0f2f5"
      sidebar-bg: "#ffffff"
      card-bg: "#ffffff"
      border: "#e4e6eb"
      border-light: "#f0f1f3"
      text-primary: "#1a1d21"
      text-secondary: "#656d76"
      text-muted: "#a5acb4"
      accent: "#0969da"
      accent-bg: "rgba(9, 105, 218, 0.08)"
      accent-hover: "rgba(9, 105, 218, 0.05)"
      green: "#1a7f37"
      green-bg: "rgba(26, 127, 55, 0.1)"
      red: "#cf222e"
      red-bg: "rgba(207, 34, 46, 0.1)"
      orange: "#bf8700"
      orange-bg: "rgba(191, 135, 0, 0.1)"
      purple: "#8250df"
      purple-bg: "rgba(130, 80, 223, 0.1)"
      cyan: "#0550ae"
      cyan-bg: "rgba(5, 80, 174, 0.08)"

    dark:
      bg: "#080c14"
      sidebar-bg: "#0e1525"
      card-bg: "#0e1525"
      border: "#1e293b"
      border-light: "#1a2332"
      text-primary: "#e2e8f0"
      text-secondary: "#94a3b8"
      text-muted: "#8b95a5"
      accent: "#3b82f6"
      accent-bg: "rgba(59, 130, 246, 0.12)"
      accent-hover: "rgba(59, 130, 246, 0.06)"
      green: "#22c55e"
      green-bg: "rgba(34, 197, 94, 0.12)"
      red: "#ef4444"
      red-bg: "rgba(239, 68, 68, 0.12)"
      orange: "#f59e0b"
      orange-bg: "rgba(245, 158, 11, 0.12)"
      purple: "#a78bfa"
      purple-bg: "rgba(167, 139, 250, 0.12)"
      cyan: "#06b6d4"
      cyan-bg: "rgba(6, 182, 212, 0.08)"

    login:
      bg-deep: "#060a14"
      bg-card: "rgba(12, 18, 32, 0.95)"
      border-subtle: "rgba(59, 130, 246, 0.08)"
      border-default: "rgba(59, 130, 246, 0.15)"
      border-strong: "rgba(59, 130, 246, 0.3)"
      text-primary: "#f0f4fc"
      text-secondary: "#8b9dc3"
      text-muted: "#4a5f8a"
      accent: "#3b82f6"
      accent-dim: "rgba(59, 130, 246, 0.12)"
      accent-red: "#ef4444"
      accent-red-dim: "rgba(239, 68, 68, 0.12)"
      input-bg: "rgba(255, 255, 255, 0.04)"
      input-border: "rgba(255, 255, 255, 0.1)"
      input-focus: "#3b82f6"
      btn-primary: "#2563eb"

    semantic:
      success: "var(--green)"
      warning: "var(--orange)"
      danger: "var(--red)"
      info: "var(--accent)"

  typography:
    font-family-ui: >-
      'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI',
      'PingFang SC', 'Microsoft YaHei', 'Helvetica Neue', sans-serif
    font-family-mono: >-
      'JetBrains Mono', 'SF Mono', Consolas, monospace
    font-size-caption: 12px
    font-size-body-sm: 14px
    font-size-body: 16px
    font-size-body-lg: 20px
    font-size-heading: 24px
    font-size-title: 32px
    font-size-display: 40px
    font-weight-regular: 400
    font-weight-medium: 500
    font-weight-semibold: 600
    font-weight-bold: 700
    font-weight-extrabold: 800
    line-height-tight: 1
    line-height-normal: 1.3
    line-height-relaxed: 1.4
    letter-spacing-tight: "-0.5px"
    letter-spacing-normal: "0"
    letter-spacing-wide: "0.5px"
    letter-spacing-wider: "0.8px"
    letter-spacing-widest: "4px"

  spacing:
    scale-unit: 1px
    space-1: 2px
    space-2: 4px
    space-3: 5px
    space-4: 6px
    space-5: 7px
    space-6: 8px
    space-7: 9px
    space-8: 10px
    space-9: 11px
    space-10: 12px
    space-11: 14px
    space-12: 15px
    space-13: 16px
    space-14: 18px
    space-15: 20px
    space-16: 22px
    space-17: 24px
    space-18: 28px
    space-19: 32px
    space-20: 36px
    space-21: 40px
    space-22: 44px
    space-23: 48px

  sizing:
    sidebar-width: 200px
    sidebar-width-collapsed: 0px
    topbar-height: 52px
    topbar-height-monitor: 48px
    sidebar-width-monitor: 260px
    sidebar-width-monitor-tablet: 220px
    button-min-height: 44px
    button-min-height-sm: 36px
    stat-icon-size: 36px
    stat-icon-size-sm: 30px
    sidebar-icon-size: 24px
    avatar-size: 26px
    cam-status-dot: 6px
    device-status-dot: 7px

  radii:
    radius-sm: 6px
    radius: 8px
    radius-md: 14px
    radius-lg: 16px
    radius-pill: 20px
    radius-full: 50%

  shadow:
    sm: "0 1px 2px rgba(0, 0, 0, 0.06)"
    default: "0 1px 3px rgba(0, 0, 0, 0.08), 0 0 0 1px rgba(0, 0, 0, 0.04)"
    md: "0 4px 12px rgba(0, 0, 0, 0.1), 0 0 0 1px rgba(0, 0, 0, 0.04)"
    login-card: "0 8px 48px rgba(0, 0, 0, 0.4)"
    dark-sm: "0 1px 2px rgba(0, 0, 0, 0.3)"
    dark: "0 1px 3px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(0, 0, 0, 0.2)"
    dark-md: "0 4px 12px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(0, 0, 0, 0.2)"

  elevation:
    base: 0
    sidebar: 100
    topbar: 50
    camera-alert-badge: 3
    hud-overlay: 2
    modal-overlay: 500
    modal: 501
    toast: 1000
    image-viewer: 600

  motion:
    duration-fast: "0.15s"
    duration-normal: "0.2s"
    duration-medium: "0.25s"
    duration-slow: "0.3s"
    duration-slower: "0.35s"
    duration-slowest: "0.5s"
    easing-default: ease
    easing-out: ease-out
    easing-in-out: ease-in-out
    easing-linear: linear
    animation-card-enter: "cardIn 0.5s ease-out both"
    animation-slide-up: "slideUp 0.3s ease both"
    animation-modal-in: "modalIn 0.2s ease"
    animation-toast-in: "toastIn 0.25s ease"
    animation-alert-pop: "alertPop 0.3s ease"
    animation-shake: "shake 0.4s ease"
    animation-spin: "spin 0.6s linear infinite"
    animation-pulse: "pulse 2s infinite"
    animation-blink: "blink 1.5s infinite"
    animation-shimmer: "shimmer 1.5s ease-in-out infinite"

  border:
    default: "1px solid var(--border)"
    light: "1px solid var(--border-light)"
    subtle: "1px solid var(--border-subtle)"
    accent: "1px solid var(--accent)"
    danger: "1px solid rgba(239, 68, 68, 0.2)"
    warning: "1px solid rgba(245, 158, 11, 0.3)"
    success: "1px solid rgba(34, 197, 94, 0.3)"

  gradient:
    video-hud: "linear-gradient(transparent, rgba(0, 0, 0, 0.7))"
    video-overlay: "linear-gradient(transparent, rgba(0, 0, 0, 0.8))"
    login-glow: >-
      radial-gradient(ellipse at 30% 30%, rgba(59, 130, 246, 0.06) 0%, transparent 50%),
      radial-gradient(ellipse at 70% 70%, rgba(6, 182, 212, 0.04) 0%, transparent 50%)
    login-grid: >-
      linear-gradient(rgba(59, 130, 246, 0.04) 1px, transparent 1px),
      linear-gradient(90deg, rgba(59, 130, 246, 0.04) 1px, transparent 1px)

  breakpoint:
    mobile: 480px
    tablet: 800px
    desktop: 1100px
    wide: 1200px

  grid:
    camera-columns: 3
    camera-rows: 2
    camera-columns-tablet: 2
    camera-rows-tablet: 3
    camera-columns-mobile: 1
    camera-rows-mobile: 6
    camera-gap: 8px
    stat-columns: 4
    stat-columns-tablet: 2
    stat-columns-mobile: 1
    device-columns: 3

  component:
    badge:
      padding: "2px 7px"
      font-size: 11px
      radius: 20px
    toast:
      min-width: 220px
      padding: "8px 13px"
      top-offset: 64px
      right-offset: 14px
    modal:
      width: 440px
      max-width: 90vw
    stat-card:
      padding: "16px 18px"
      value-size: 26px
    form-input:
      height: 44px
      padding: "10px 12px"
    login-card:
      max-width: 420px
      padding: "48px 40px 36px"
    login-input:
      height: 44px
      padding: "0 14px"
    login-btn:
      height: 46px
    scrollbar:
      width: 5px
      thumb-radius: 3px
    cam-panel:
      header-height: 32px

---

## Look & Feel

The system serves two distinct visual contexts that share a single design
language but diverge in atmosphere.

### Login — Immersive Dark Portal

The login screen is an atmospheric entry point. A near-black background
(`#060a14`) is pierced by a subtle blue grid pattern and radial glow
gradients, creating a sense of depth without decoration. The login card
floats above this with a frosted-glass feel — semi-transparent dark
background, a razor-thin blue border, and a heavy drop shadow. The card
enters with a smooth fade-and-rise animation (`cardIn`). On auth failure
the card shakes horizontally. The primary button is a solid blue bar
with wide letter-spacing, conveying authority. The entire page is
dark-only; there is no light variant for the login screen.

### Admin Panels — Clean Light Dashboard

The admin and index pages use a conventional light dashboard layout:
white sidebar on the left, white topbar, gray page background. Cards
have a flat appearance with a subtle 1px border and almost-invisible
shadow; on hover they lift slightly and gain a stronger shadow. The
accent blue (`#0969da`) is used sparingly — active sidebar items get a
blue left-indicator bar, stat icons sit in blue-tinted circles, and
focus rings are blue. Data values use JetBrains Mono for tabular
alignment. The sidebar collapses to zero width below 800px with a
toggle button appearing in the top-left corner.

### Monitor Wall — Cinematic Dark Grid

The monitoring dashboard (`monitor.css`) is permanently dark, designed
for large displays in a control room. The page has no scroll — it fills
100vh with a 3x2 camera grid on the left and a 260px alert/device
sidebar on the right. Camera panels have a black video background with
a gradient HUD overlay at the bottom showing person count and
timestamp. Alert badges float in the top-right corner with a red
background and pop-in animation. The topbar shows live stat chips
(detection count, active alerts, FPS) in monospace with colored
borders for alert (red) and online (green) states. The overall feel is
dark, data-dense, and scan-friendly — everything is designed to be
read at a glance from several meters away.

### Motion Philosophy

Animations are fast and functional, never decorative. Entry animations
use staggered delays (`slideUp` with 20-40ms increments per card) so
content appears to cascade in. The `shimmer` skeleton loader uses a
left-to-right gradient sweep during data fetches. Status indicators
pulse (`pulse` for warning dots, `blink` for recording indicators) to
draw attention without being distracting. Toast notifications slide in
from the right and auto-dismiss after 3.5 seconds. All transitions
complete in under 300ms except the login card entrance (500ms) and
the infinite skeleton shimmer (1.5s loop).

### Typography Strategy

Inter handles all UI text — navigation, labels, headings, body copy.
JetBrains Mono is reserved for data: stat values, timestamps, FPS
counters, device metadata, and code-adjacent content. The split
creates a clear visual hierarchy: human-readable text in Inter,
machine-readable numbers in monospace. Font sizes follow the Major Third scale (1.25 ratio) centered on 16px base. Dashboard uses body-sm (14px) through title (32px); the login page and monitor wall use the full range from caption (12px) to display (40px).

### Color Semantics

The five semantic colors map directly to detection types:
- **Red** (`--red`) — 跌倒 (fall), 打架 (fight), critical alerts
- **Orange** (`--orange`) — warnings, offline indicators
- **Green** (`--green`) — online status, success states
- **Blue** (`--accent`) — primary actions, focus, active navigation
- **Purple** (`--purple`) — 疲劳 (fatigue) detection type

Each semantic color has a matching background tint (e.g., `--red-bg`)
used for badges, stat icons, and alert item borders. The tints are
low-opacity versions of the main color, keeping the UI calm even when
multiple alert types are visible simultaneously.

### Accessibility

The design enforces a 44px minimum touch/click target across all
interactive elements (buttons, sidebar items, nav links, camera
fullscreen button). Focus-visible outlines use the accent blue with
2px offset. The dark theme maintains WCAG-compliant contrast ratios
for primary text (`#e2e8f0` on `#080c14`) and secondary text
(`#94a3b8` on `#080c14`). A skip-to-content link is present on the
monitor page for keyboard users.
