import { useRef, useMemo, useState, useEffect } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Html, OrbitControls } from "@react-three/drei";
import * as THREE from "three";

// ── Types ──────────────────────────────────────────────────────────────────

interface Bldg {
  id: string; name: string;
  x: number; y: number; w: number; h: number;
  floors: number; intensity: number; alerts: number;
  top: string; zone: "front" | "back";
}

// ── Building Data (SVG viewBox coords) ─────────────────────────────────────

const BLDGS: Bldg[] = [
  { id: "A", name: "一监区监舍楼", x: 80,  y: 100, w: 130, h: 70, floors: 4, intensity: 82, alerts: 18, top: "打架", zone: "back" },
  { id: "B", name: "二监区监舍楼", x: 230, y: 100, w: 130, h: 70, floors: 4, intensity: 45, alerts: 7, top: "人员聚集", zone: "back" },
  { id: "C", name: "三监区监舍楼", x: 380, y: 100, w: 130, h: 70, floors: 4, intensity: 28, alerts: 3, top: "跌倒", zone: "back" },
  { id: "D", name: "监控指挥中心", x: 530, y: 100, w: 80,  h: 70, floors: 3, intensity: 15, alerts: 1, top: "跌倒", zone: "back" },
  { id: "E", name: "生产车间",     x: 80,  y: 220, w: 170, h: 80, floors: 1, intensity: 65, alerts: 12, top: "离岗", zone: "back" },
  { id: "F", name: "食堂",         x: 300, y: 220, w: 130, h: 80, floors: 1, intensity: 35, alerts: 5, top: "打架", zone: "back" },
  { id: "G", name: "教学楼",       x: 80,  y: 350, w: 110, h: 65, floors: 2, intensity: 20, alerts: 2, top: "离岗", zone: "back" },
  { id: "H", name: "医务室",       x: 220, y: 350, w: 80,  h: 65, floors: 1, intensity: 10, alerts: 1, top: "跌倒", zone: "back" },
  { id: "I", name: "会见室",       x: 340, y: 350, w: 110, h: 65, floors: 1, intensity: 30, alerts: 4, top: "人员聚集", zone: "back" },
  { id: "J", name: "行政办公楼",   x: 130, y: 470, w: 130, h: 55, floors: 3, intensity: 0, alerts: 0, top: "—", zone: "front" },
  { id: "K", name: "武警营房",     x: 310, y: 470, w: 100, h: 55, floors: 2, intensity: 0, alerts: 0, top: "—", zone: "front" },
  { id: "L", name: "备勤楼",       x: 460, y: 470, w: 100, h: 55, floors: 2, intensity: 0, alerts: 0, top: "—", zone: "front" },
];

const BACK = BLDGS.filter(b => b.zone === "back");

// ── 3D Constants ───────────────────────────────────────────────────────────

const SCALE = 0.1;
const GROUND_Y = 0;
const FLOOR_H = 1.0;
const WALL_H = 3.0;

function svgTo3D(sx: number, sy: number, z = 0): [number, number, number] {
  return [(sx - 400) * SCALE, z, (sy - 280) * SCALE];
}

function heatColor(t: number) {
  const c = Math.max(0, Math.min(1, t));
  if (c > 0.65) return new THREE.Color().lerpColors(
    new THREE.Color(0x33cc00ff).setRGB(51/255, 204/255, 230/255),
    new THREE.Color(0xe6261f).setRGB(230/255, 38/255, 31/255),
    (c - 0.65) / 0.35,
  );
  return new THREE.Color().lerpColors(
    new THREE.Color(0x0fd9b5).setRGB(13/255, 242/255, 217/255),
    new THREE.Color(0x33cc00ff).setRGB(51/255, 204/255, 230/255),
    c / 0.65,
  );
}

// ── Label visibility (hide overlapping low-priority labels) ─────────────────

// FIX: 之前用 zOff/yExtra 推移标签，配合 distanceFactor 导致 center 偏移
// 改为：去掉 distanceFactor（center 精确居中），重叠时隐藏低优先级标签
const LABEL_HIDDEN = (() => {
  const hidden = new Set<string>();
  // Group by row
  const rows = new Map<number, Bldg[]>();
  for (const b of BLDGS) {
    const list = rows.get(b.y) ?? [];
    list.push(b);
    rows.set(b.y, list);
  }
  for (const [, buildings] of rows) {
    const sorted = [...buildings].sort((a, b) => a.x - b.x);
    for (let i = 0; i < sorted.length - 1; i++) {
      const gap = (sorted[i+1].x - (sorted[i].x + sorted[i].w)) * SCALE;
      if (gap < 1.5) {
        // Hide lower-priority label (fewer alerts = lower priority)
        const loser = sorted[i].alerts >= sorted[i+1].alerts ? i + 1 : i;
        hidden.add(sorted[loser].id);
      }
    }
  }
  return hidden;
})();

// ── Heat Dots (floating particles inside building) ─────────────────────────

function HeatDots({ b }: { b: Bldg }) {
  const count = Math.max(4, Math.round(b.intensity * 0.12));
  const color = heatColor(b.intensity / 100);

  const positions = useMemo(() => {
    const [cx, , cz] = svgTo3D(b.x + b.w / 2, b.y + b.h / 2);
    const hw = b.w * SCALE * 0.35;
    const hd = b.h * SCALE * 0.35;
    return Array.from({ length: count }, () => ({
      x: cx + (Math.random() - 0.5) * hw * 2,
      y: GROUND_Y + 0.3 + Math.random() * b.floors * FLOOR_H * 0.8,
      z: cz + (Math.random() - 0.5) * hd * 2,
      speed: 0.3 + Math.random() * 0.5,
      offset: Math.random() * Math.PI * 2,
    }));
  }, [b, count]);

  return (
    <group>
      {positions.map((p, i) => (
        <HeatDot key={i} pos={p} color={color} />
      ))}
    </group>
  );
}

function HeatDot({ pos, color }: { pos: { x: number; y: number; z: number; speed: number; offset: number }; color: THREE.Color }) {
  const ref = useRef<THREE.Mesh>(null);
  useFrame(({ clock }) => {
    if (!ref.current) return;
    const t = clock.getElapsedTime() * pos.speed + pos.offset;
    ref.current.position.y = pos.y + Math.sin(t) * 0.5;
    (ref.current.material as THREE.MeshBasicMaterial).opacity = 0.3 + Math.sin(t * 2) * 0.3;
  });
  return (
    <mesh ref={ref} position={[pos.x, pos.y, pos.z]}>
      <sphereGeometry args={[0.3, 8, 8]} />
      <meshBasicMaterial color={color} transparent opacity={0.5} />
    </mesh>
  );
}

// ── Zone Divider (low fence wall) ──────────────────────────────────────────

function ZoneDivider({ start, end, y = 0.75 }: {
  start: [number, number, number]; end: [number, number, number]; y?: number;
}) {
  const dx = end[0] - start[0];
  const dz = end[2] - start[2];
  const len = Math.sqrt(dx * dx + dz * dz);
  const angle = Math.atan2(dx, dz);
  return (
    <mesh position={[(start[0] + end[0]) / 2, y, (start[2] + end[2]) / 2]} rotation={[0, angle, 0]}>
      <boxGeometry args={[0.1, 1.5, len]} />
      <meshBasicMaterial color="#06b6d4" transparent opacity={0.35} />
    </mesh>
  );
}

// ── Patrol Path (inner ring) ───────────────────────────────────────────────

function PatrolPath() {
  const pts = useMemo(() => {
    const [a, , b] = svgTo3D(56, 76);
    const [c, , d] = svgTo3D(744, 76);
    const [e, , f] = svgTo3D(744, 504);
    const [g, , h] = svgTo3D(56, 504);
    return [new THREE.Vector3(a, 0.1, b), new THREE.Vector3(c, 0.1, d),
      new THREE.Vector3(e, 0.1, f), new THREE.Vector3(g, 0.1, h)];
  }, []);
  return (
    <lineLoop>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position"
          args={[new Float32Array(pts.flatMap(p => [p.x, p.y, p.z])), 3]} />
      </bufferGeometry>
      <lineBasicMaterial color="#22d3ee" transparent opacity={0.12} />
    </lineLoop>
  );
}

// ── Scan Curtain (vertical light plane) ────────────────────────────────────

function ScanCurtain() {
  const ref = useRef<THREE.Mesh>(null);
  const startX = -35;
  const endX = 35;
  useFrame(({ clock }) => {
    if (!ref.current) return;
    const t = (Math.sin(clock.getElapsedTime() * Math.PI / 3) + 1) / 2;
    ref.current.position.x = startX + (endX - startX) * t;
  });
  return (
    <mesh ref={ref} position={[0, 2, 0]} rotation={[0, Math.PI / 2, 0]}>
      <planeGeometry args={[50, 4]} />
      <meshBasicMaterial color="#22d3ee" transparent opacity={0.06} side={THREE.DoubleSide} />
    </mesh>
  );
}

// ── Zone Label (raised above buildings) ────────────────────────────────────

function ZoneLabel3D({ pos, text }: { pos: [number, number, number]; text: string }) {
  return (
    // FIX: 去掉 distanceFactor，center 精确定位，固定像素大小不漂移
    <Html position={pos} center style={{ pointerEvents: "none" }}>
      <div style={{
        color: "rgba(14,165,233,0.4)", fontSize: 11, fontFamily: "monospace",
        letterSpacing: 4, whiteSpace: "nowrap", textTransform: "uppercase",
      }}>{text}</div>
    </Html>
  );
}

// ── Compass (3D) ───────────────────────────────────────────────────────────

function Compass3D() {
  return (
    // FIX: 去掉 distanceFactor，固定像素大小
    <Html position={svgTo3D(720, 500, 0)} center style={{ pointerEvents: "none" }}>
      <div style={{ textAlign: "center" }}>
        <div style={{
          width: 28, height: 28, borderRadius: "50%",
          border: "1px solid rgba(14,165,233,0.25)", margin: "0 auto",
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <span style={{ color: "#22d3ee", fontSize: 10, fontWeight: 700, fontFamily: "monospace" }}>N</span>
        </div>
      </div>
    </Html>
  );
}

// ── Building Label (anti-overlap) ──────────────────────────────────────────

function BuildingLabel({ b }: { b: Bldg }) {
  // FIX: 隐藏重叠标签（gap<1.5 的同排建筑中低优先级者）
  if (LABEL_HIDDEN.has(b.id)) return null;

  const isBack = b.zone === "back";
  const h = b.floors * FLOOR_H + 0.3;
  const [x, , z] = svgTo3D(b.x + b.w / 2, b.y + b.h / 2);

  // FIX: 去掉 distanceFactor，center 精确居中到建筑顶部中心
  // distanceFactor 会缩放 CSS transform 偏移量，导致标签漂移
  return (
    <Html position={[x, h + 0.3, z]} center style={{ pointerEvents: "none" }}>
      <div style={{
        background: "rgba(2,6,23,0.92)",
        border: `1px solid ${isBack ? "rgba(14,165,233,0.4)" : "rgba(100,116,139,0.25)"}`,
        borderRadius: 6, padding: "4px 8px", textAlign: "center",
        backdropFilter: "blur(8px)", whiteSpace: "nowrap",
        boxShadow: isBack && b.intensity > 60
          ? `0 0 12px ${heatColor(b.intensity / 100).getStyle()}40`
          : "none",
      }}>
        <div style={{
          color: isBack ? "#e2e8f0" : "#94a3b8",
          fontSize: 11, fontWeight: 700, fontFamily: "monospace",
        }}>{b.name}</div>
        {isBack && (
          <div style={{
            color: heatColor(b.intensity / 100).getStyle(),
            fontSize: 9, fontFamily: "monospace", marginTop: 1,
          }}>
            {b.intensity}% · {b.alerts}告警 · {b.top}
          </div>
        )}
      </div>
    </Html>
  );
}

// ── Building 3D ────────────────────────────────────────────────────────────

function Building3D({ b }: { b: Bldg }) {
  const isBack = b.zone === "back";
  const h = b.floors * FLOOR_H;
  const w = b.w * SCALE;
  const d = b.h * SCALE;
  const [cx, , cz] = svgTo3D(b.x + b.w / 2, b.y + b.h / 2);

  const wallColor = isBack ? "#155e75" : "#475569";
  const roofColor = isBack ? "#0891b2" : "#64748b";
  const heat = isBack ? heatColor(b.intensity / 100) : null;

  const edgeRef = useRef<THREE.Mesh>(null);

  useFrame(({ clock }) => {
    if (!edgeRef.current || !heat) return;
    const p = 0.2 + Math.sin(clock.getElapsedTime() * 1.5) * 0.2;
    (edgeRef.current.material as THREE.MeshBasicMaterial).opacity = p;
  });

  return (
    <group position={[cx, GROUND_Y + h / 2, cz]}>
      {/* body */}
      <mesh>
        <boxGeometry args={[w, h, d]} />
        <meshBasicMaterial
          color={wallColor}
          transparent opacity={0.9}
        />
      </mesh>

      {/* roof slab */}
      <mesh position={[0, h / 2 + 0.04, 0]}>
        <boxGeometry args={[w + 0.06, 0.08, d + 0.06]} />
        <meshBasicMaterial color={roofColor} />
      </mesh>

      {/* floor separators */}
      {b.floors > 1 && Array.from({ length: b.floors - 1 }, (_, i) => (
        <mesh key={i} position={[0, -h / 2 + (i + 1) * FLOOR_H, 0]}>
          <boxGeometry args={[w + 0.02, 0.03, d + 0.02]} />
          <meshBasicMaterial color={roofColor} transparent opacity={0.6} />
        </mesh>
      ))}

      {/* heat edge glow */}
      {heat && (
        <mesh ref={edgeRef}>
          <boxGeometry args={[w + 0.06, h + 0.06, d + 0.06]} />
          <meshBasicMaterial color={heat} transparent opacity={0.3} wireframe />
        </mesh>
      )}

      {/* heat light (high intensity) */}
      {isBack && b.intensity > 50 && (
        <pointLight color={heat!.getStyle()} intensity={b.intensity * 0.03} distance={6} position={[0, h / 2, 0]} />
      )}

      {/* floating dots */}
      {isBack && b.intensity > 10 && <HeatDots b={b} />}

      {/* label */}
      <BuildingLabel b={b} />
    </group>
  );
}

// ── Watchtower 3D ──────────────────────────────────────────────────────────

function Watchtower3D({ pos }: { pos: [number, number, number] }) {
  const ref = useRef<THREE.Mesh>(null);
  useFrame(({ clock }) => {
    if (!ref.current) return;
    (ref.current.material as THREE.MeshBasicMaterial).opacity = 0.4 + Math.sin(clock.getElapsedTime() * 3) * 0.4;
  });

  return (
    <group position={pos}>
      <mesh position={[0, 2, 0]}>
        <boxGeometry args={[1.5, 4, 1.5]} />
        <meshBasicMaterial color="#1e3a5f" transparent opacity={0.9} />
      </mesh>
      <mesh position={[0, 4.2, 0]}>
        <sphereGeometry args={[0.3, 16, 16]} />
        <meshBasicMaterial color="#f87171" />
      </mesh>
      <mesh ref={ref} position={[0, 4.2, 0]}>
        <sphereGeometry args={[0.6, 16, 16]} />
        <meshBasicMaterial color="#f87171" transparent opacity={0.3} />
      </mesh>
      <pointLight color="#f87171" intensity={1} distance={8} position={[0, 4.2, 0]} />
    </group>
  );
}

// ── HUD (3D) ───────────────────────────────────────────────────────────────

function Hud3D() {
  const [time, setTime] = useState(new Date().toLocaleTimeString("zh-CN"));
  useEffect(() => {
    const id = setInterval(() => setTime(new Date().toLocaleTimeString("zh-CN")), 1000);
    return () => clearInterval(id);
  }, []);

  const totalAlerts = BACK.reduce((s, b) => s + b.alerts, 0);
  const highRisk = BACK.filter(b => b.intensity > 60).length;

  // Position at top-right of the scene in 3D
  const pos = svgTo3D(780, 30, 6);

  return (
    <Html position={pos} center={false} distanceFactor={25} style={{ pointerEvents: "none" }}>
      <div style={{ textAlign: "right", minWidth: 120 }}>
        <div style={{ color: "rgba(34,211,238,0.5)", fontFamily: "monospace", fontSize: 9, letterSpacing: 2 }}>SYS_TIME</div>
        <div style={{ color: "#22d3ee", fontFamily: "monospace", fontSize: 13, fontWeight: 700, fontVariantNumeric: "tabular-nums" }}>{time}</div>
        <div style={{ marginTop: 8 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: 6, marginBottom: 3 }}>
            <span style={{ color: "rgba(34,211,238,0.4)", fontFamily: "monospace", fontSize: 9 }}>ALERTS</span>
            <span style={{ color: "#fbbf24", fontFamily: "monospace", fontSize: 12, fontWeight: 700 }}>{totalAlerts}</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: 6, marginBottom: 3 }}>
            <span style={{ color: "rgba(34,211,238,0.4)", fontFamily: "monospace", fontSize: 9 }}>HIGH_RISK</span>
            <span style={{ color: "#f87171", fontFamily: "monospace", fontSize: 12, fontWeight: 700 }}>{highRisk}</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: 6 }}>
            <span style={{ color: "rgba(34,211,238,0.4)", fontFamily: "monospace", fontSize: 9 }}>BUILDINGS</span>
            <span style={{ color: "#22d3ee", fontFamily: "monospace", fontSize: 12, fontWeight: 700 }}>{BLDGS.length}</span>
          </div>
        </div>
      </div>
    </Html>
  );
}

// ── Legend (3D) ────────────────────────────────────────────────────────────

function Legend3D() {
  const pos = svgTo3D(780, 540, 0);
  return (
    <Html position={pos} center={false} distanceFactor={25} style={{ pointerEvents: "none" }}>
      <div style={{
        background: "rgba(15,23,42,0.85)", backdropFilter: "blur(4px)",
        border: "1px solid rgba(21,94,117,0.3)", borderRadius: 8, padding: "8px 10px",
      }}>
        <p style={{ color: "rgba(34,211,238,0.5)", fontFamily: "monospace", fontSize: 9, textTransform: "uppercase", letterSpacing: 2, margin: "0 0 6px 0" }}>异常密度</p>
        <div style={{ width: 90, height: 5, borderRadius: 3, background: "linear-gradient(to right, #0fd9b5, #f59e0b, #ef4444)" }} />
        <div style={{ display: "flex", justifyContent: "space-between", fontFamily: "monospace", fontSize: 9, color: "rgba(34,211,238,0.4)", marginTop: 4 }}>
          <span>LOW</span><span>HIGH</span>
        </div>
      </div>
    </Html>
  );
}

// ── Main Scene ─────────────────────────────────────────────────────────────

function Scene() {
  const [wx, , wz] = svgTo3D(400, 70);
  const [ww, , wd] = [700 * SCALE, 0, 480 * SCALE];

  return (
    <>
      {/* lighting */}
      <ambientLight intensity={0.4} />
      <directionalLight position={[15, 20, 10]} intensity={0.8} castShadow
        shadow-mapSize-width={1024} shadow-mapSize-height={1024}
        shadow-camera-far={80} shadow-camera-left={-15} shadow-camera-right={15}
        shadow-camera-top={15} shadow-camera-bottom={-15}
      />
      <directionalLight position={[-10, 8, -5]} intensity={0.25} color="#60a5fa" />

      {/* ground */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, GROUND_Y - 0.01, 0]}>
        <planeGeometry args={[120, 120]} />
        <meshBasicMaterial color="#080e1a" />
      </mesh>

      {/* ground grid — reduced density */}
      <gridHelper args={[120, 60, "#0e2a47", "#0a1e36"]} position={[0, GROUND_Y, 0]} />

      {/* perimeter walls — expanded to properly enclose all buildings */}
      <group>
        {/* north — above back row (buildings end at z=-11) */}
        <mesh position={[wx, WALL_H / 2, wz - wd / 2 - 3]}>
          <boxGeometry args={[ww + 6, WALL_H, 0.3]} />
          <meshBasicMaterial color="#2563eb" transparent opacity={0.5} />
        </mesh>
        {/* south — below front zone (buildings end at z=22.5) */}
        <mesh position={[wx, WALL_H / 2, wz + wd / 2 + 4]}>
          <boxGeometry args={[ww + 6, WALL_H, 0.3]} />
          <meshBasicMaterial color="#2563eb" transparent opacity={0.5} />
        </mesh>
        {/* west */}
        <mesh position={[wx - ww / 2 - 3, WALL_H / 2, wz + 0.5]}>
          <boxGeometry args={[0.3, WALL_H, wd + 7]} />
          <meshBasicMaterial color="#2563eb" transparent opacity={0.5} />
        </mesh>
        {/* east */}
        <mesh position={[wx + ww / 2 + 3, WALL_H / 2, wz + 0.5]}>
          <boxGeometry args={[0.3, WALL_H, wd + 7]} />
          <meshBasicMaterial color="#2563eb" transparent opacity={0.5} />
        </mesh>
      </group>

      {/* AB gate */}
      <mesh position={svgTo3D(400, 540, WALL_H / 2)}>
        <boxGeometry args={[4, WALL_H, 0.4]} />
        <meshBasicMaterial color="#fbbf24" transparent opacity={0.3} />
      </mesh>

      {/* patrol path */}
      <PatrolPath />

      {/* zone dividers (low fence walls) */}
      <ZoneDivider start={svgTo3D(60, 190)} end={svgTo3D(740, 190)} />
      <ZoneDivider start={svgTo3D(60, 320)} end={svgTo3D(740, 320)} />
      <ZoneDivider start={svgTo3D(260, 195)} end={svgTo3D(260, 315)} />
      <ZoneDivider start={svgTo3D(330, 325)} end={svgTo3D(330, 430)} />

      {/* scan curtain — lowered to ground level */}
      <ScanCurtain />

      {/* zone labels — raised above all buildings (max building top ≈ y=4.3) */}
      <ZoneLabel3D pos={svgTo3D(400, 85, 6)} text="监管区（后区）" />
      <ZoneLabel3D pos={svgTo3D(400, 255, 3)} text="劳动生活区" />
      <ZoneLabel3D pos={svgTo3D(400, 385, 3.5)} text="教育服务区" />
      <ZoneLabel3D pos={svgTo3D(400, 455, 4.5)} text="行政区（前区）" />

      {/* compass */}
      <Compass3D />

      {/* buildings */}
      {BLDGS.map(b => <Building3D key={b.id} b={b} />)}

      {/* watchtowers */}
      <Watchtower3D pos={svgTo3D(50, 50, 0)} />
      <Watchtower3D pos={svgTo3D(750, 50, 0)} />
      <Watchtower3D pos={svgTo3D(50, 510, 0)} />
      <Watchtower3D pos={svgTo3D(750, 510, 0)} />

      {/* HUD + Legend (3D positioned) */}
      <Hud3D />
      <Legend3D />

      {/* orbit controls */}
      <OrbitControls
        enablePan={false}
        minDistance={15} maxDistance={80}
        minPolarAngle={0.3} maxPolarAngle={Math.PI / 2.2}
        autoRotate autoRotateSpeed={0.4}
        target={[0, 2, 0]}
      />
    </>
  );
}

// ── Export ──────────────────────────────────────────────────────────────────

export default function Prison3D() {
  return (
    <div className="relative w-full h-full rounded-xl overflow-hidden bg-slate-950">
      <Canvas
        camera={{ position: [40, 50, 40], fov: 35, near: 0.1, far: 300 }}
        style={{ position: "absolute", inset: 0 }}
        gl={{ antialias: true }}
      >
        <Scene />
      </Canvas>
    </div>
  );
}
