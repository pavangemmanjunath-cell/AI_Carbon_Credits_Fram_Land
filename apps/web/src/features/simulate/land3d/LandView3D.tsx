/**
 * 3D view of the plot and its trees (React Three Fiber). Loaded lazily by the
 * Simulation page, so three.js is only downloaded when the 3D view is opened.
 *
 * It renders; it does not calculate. Sizes, positions and carbon come from
 * ./landScene (config values and the simulation engine's series).
 */
import { useLayoutEffect, useMemo, useRef, useState } from 'react';
import { Canvas, type ThreeEvent } from '@react-three/fiber';
import { Grid, Html, Line, OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import { Minus, Plus, RotateCcw, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { formatNumber } from '@/lib/format';
import type { Species } from '@/types/api';
import {
  bounds,
  layoutTrees,
  treeSize,
  type Point,
  type TreeLayout,
  type TreeSize,
  type YearCarbon,
} from './landScene';
import './i18n';

export interface LandView3DProps {
  ring: Point[];
  boundarySaved: boolean;
  treeCount: number;
  areaHectares: number;
  growth: number;
  age: number;
  standYear: number;
  species?: Species;
  speciesName: string;
  carbon: YearCarbon | null;
  locale: string;
}

type Selection = { kind: 'plot' } | { kind: 'tree'; index: number } | null;

interface Controls {
  object: THREE.Camera;
  target: THREE.Vector3;
  update: () => void;
}

const PLOT_HEIGHT = 0.35;
const CROWN = new THREE.Color('#4f9a5b');
const CROWN_SELECTED = new THREE.Color('#f0a43a');
const TRUNK = new THREE.Color('#7a5a3c');

/** Deterministic 0–1 value per tree, so the stand looks natural but never flickers. */
function jitter(i: number, salt: number): number {
  const x = Math.sin(i * 12.9898 + salt * 78.233) * 43758.5453;
  return x - Math.floor(x);
}

function extentOf(ring: Point[]): number {
  const b = bounds(ring);
  return Math.max(20, Math.abs(b.minX), Math.abs(b.maxX), Math.abs(b.minY), Math.abs(b.maxY));
}

function PlotMesh({
  ring,
  growth,
  selected,
  onSelect,
}: {
  ring: Point[];
  growth: number;
  selected: boolean;
  onSelect: () => void;
}) {
  const geometry = useMemo(() => {
    const shape = new THREE.Shape(ring.map(([x, y]) => new THREE.Vector2(x, y)));
    const g = new THREE.ExtrudeGeometry(shape, { depth: PLOT_HEIGHT, bevelEnabled: false });
    g.rotateX(-Math.PI / 2); // shape y (north) → −z; extrusion → +y
    return g;
  }, [ring]);
  // Bare tilled soil at planting, greener ground cover as the canopy closes (look only).
  const color = useMemo(
    () => new THREE.Color('#c8a877').lerp(new THREE.Color('#93bd7e'), Math.min(1, growth * 0.9)),
    [growth],
  );
  const outline = useMemo(
    () =>
      [...ring, ring[0]].map(([x, y]) => [x, PLOT_HEIGHT + 0.06, -y] as [number, number, number]),
    [ring],
  );
  const post = Math.max(0.25, extentOf(ring) * 0.006);
  return (
    <group>
      <mesh
        geometry={geometry}
        receiveShadow
        onClick={(e) => {
          e.stopPropagation();
          onSelect();
        }}
        onPointerOver={() => (document.body.style.cursor = 'pointer')}
        onPointerOut={() => (document.body.style.cursor = '')}
      >
        <meshStandardMaterial color={color} roughness={0.95} />
      </mesh>
      <Line
        points={outline}
        color={selected ? '#f0a43a' : '#1f6b45'}
        lineWidth={selected ? 4 : 3}
      />
      {ring.map(([x, y], i) => (
        <mesh key={i} position={[x, PLOT_HEIGHT + post * 2, -y]} castShadow>
          <cylinderGeometry args={[post, post, post * 4, 10]} />
          <meshStandardMaterial color="#ffffff" />
        </mesh>
      ))}
    </group>
  );
}

function Trees({
  layout,
  size,
  selectedIndex,
  onSelect,
}: {
  layout: TreeLayout;
  size: TreeSize;
  selectedIndex: number | null;
  onSelect: (i: number) => void;
}) {
  const trunks = useRef<THREE.InstancedMesh>(null);
  const crowns = useRef<THREE.InstancedMesh>(null);
  const count = layout.positions.length;

  useLayoutEffect(() => {
    if (!trunks.current || !crowns.current) return;
    const m = new THREE.Matrix4();
    const q = new THREE.Quaternion();
    const s = new THREE.Vector3();
    const p = new THREE.Vector3();
    const up = new THREE.Vector3(0, 1, 0);
    const c = new THREE.Color();
    layout.positions.forEach(([x, y], i) => {
      const k = 0.92 + jitter(i, 1) * 0.16; // ±8 % natural variation
      const height = Math.max(0.3, size.drawHeight * k);
      const crownR = Math.max(0.15, (size.drawCrown / 2) * k);
      const trunkH = height * 0.38;
      const trunkR = Math.max(0.04, crownR * 0.12);
      q.setFromAxisAngle(up, jitter(i, 2) * Math.PI * 2);
      m.compose(p.set(x, PLOT_HEIGHT + trunkH / 2, -y), q, s.set(trunkR, trunkH, trunkR));
      trunks.current!.setMatrixAt(i, m);
      trunks.current!.setColorAt(i, TRUNK);
      const crownHalf = Math.max(crownR * 0.6, (height - trunkH) / 2);
      m.compose(
        p.set(x, PLOT_HEIGHT + trunkH + crownHalf * 0.9, -y),
        q,
        s.set(crownR, crownHalf, crownR),
      );
      crowns.current!.setMatrixAt(i, m);
      c.copy(i === selectedIndex ? CROWN_SELECTED : CROWN).offsetHSL(
        (jitter(i, 3) - 0.5) * 0.03,
        0,
        (jitter(i, 4) - 0.5) * 0.08,
      );
      crowns.current!.setColorAt(i, c);
    });
    for (const mesh of [trunks.current, crowns.current]) {
      mesh.count = count;
      mesh.instanceMatrix.needsUpdate = true;
      if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
      mesh.computeBoundingSphere();
    }
  }, [layout, size, selectedIndex, count]);

  const pick = (e: ThreeEvent<MouseEvent>) => {
    e.stopPropagation();
    if (e.instanceId !== undefined) onSelect(e.instanceId);
  };
  const capacity = Math.max(1, count);
  return (
    <group>
      <instancedMesh
        key={`t${capacity}`}
        ref={trunks}
        args={[undefined, undefined, capacity]}
        castShadow
        onClick={pick}
      >
        <cylinderGeometry args={[0.8, 1, 1, 7]} />
        <meshStandardMaterial roughness={0.9} />
      </instancedMesh>
      <instancedMesh
        key={`c${capacity}`}
        ref={crowns}
        args={[undefined, undefined, capacity]}
        castShadow
        receiveShadow
        onClick={pick}
        onPointerOver={() => (document.body.style.cursor = 'pointer')}
        onPointerOut={() => (document.body.style.cursor = '')}
      >
        <icosahedronGeometry args={[1, 1]} />
        <meshStandardMaterial flatShading roughness={0.8} />
      </instancedMesh>
    </group>
  );
}

function Kpi({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div className="rounded-[12px] border border-white/70 bg-white/90 px-3 py-2 shadow-sm backdrop-blur">
      <span className="block text-[11px] font-medium text-ink-2">{label}</span>
      <span className="block font-mono text-[18px] font-semibold leading-tight text-ink">
        {value}
      </span>
      <span className="block text-[10.5px] text-muted">{sub}</span>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-3 border-b border-line py-1.5 text-[12.5px] last:border-0">
      <span className="text-ink-2">{label}</span>
      <span className="text-right font-mono text-ink">{value}</span>
    </div>
  );
}

export default function LandView3D(props: LandView3DProps) {
  const {
    ring,
    boundarySaved,
    treeCount,
    areaHectares,
    growth,
    age,
    standYear,
    species,
    speciesName,
    carbon,
    locale,
  } = props;
  const { t } = useTranslation();
  const [selected, setSelected] = useState<Selection>(null);
  const controls = useRef<Controls | null>(null);

  const layout = useMemo(() => layoutTrees(ring, treeCount), [ring, treeCount]);
  const size = useMemo(
    () => treeSize(species, growth, layout.spacing),
    [species, growth, layout.spacing],
  );
  const R = useMemo(() => extentOf(ring), [ring]);
  // Far enough that the whole boundary fits the 35° view (distance ≈ 3.4 × the plot radius).
  const home = useMemo(() => new THREE.Vector3(R * 1.75, R * 2.0, R * 2.2), [R]);
  const fmt = (v: number | null | undefined, digits = 1) =>
    v === null || v === undefined
      ? '—'
      : formatNumber(v, locale, { maximumFractionDigits: digits });
  const stage =
    growth < 0.3
      ? t('land3d.stageEstablishing')
      : growth < 1
        ? t('land3d.stageGrowing')
        : t('land3d.stageMature');
  const selectedIndex = selected?.kind === 'tree' ? selected.index : null;

  const dolly = (factor: number) => {
    const c = controls.current;
    if (!c) return;
    const offset = c.object.position.clone().sub(c.target).multiplyScalar(factor);
    c.object.position.copy(c.target.clone().add(offset));
    c.update();
  };
  const reset = () => {
    const c = controls.current;
    if (!c) return;
    c.target.set(0, 0, 0);
    c.object.position.copy(home);
    c.update();
  };

  const tree = selectedIndex !== null ? layout.positions[selectedIndex] : null;
  const treeTop = size.drawHeight + PLOT_HEIGHT + 0.5;

  return (
    <div
      className="relative h-[540px] w-full"
      aria-label={t('land3d.sceneLabel', { year: standYear, count: treeCount, age })}
      role="img"
    >
      <Canvas
        shadows
        dpr={[1, 2]}
        camera={{ position: home.toArray(), fov: 35, near: 0.5, far: R * 30 }}
        onPointerMissed={() => setSelected(null)}
        gl={{ antialias: true, preserveDrawingBuffer: true }}
      >
        <color attach="background" args={['#eef3ea']} />
        <fog attach="fog" args={['#eef3ea', R * 3.5, R * 9]} />
        <hemisphereLight args={['#ffffff', '#c9d6c0', 0.95]} />
        <directionalLight
          castShadow
          position={[R * 0.9, R * 1.6, R * 0.5]}
          intensity={1.5}
          shadow-mapSize={[2048, 2048]}
          shadow-camera-left={-R * 1.4}
          shadow-camera-right={R * 1.4}
          shadow-camera-top={R * 1.4}
          shadow-camera-bottom={-R * 1.4}
          shadow-camera-far={R * 5}
          shadow-bias={-0.0004}
        />
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]} receiveShadow>
          <planeGeometry args={[R * 14, R * 14]} />
          <meshStandardMaterial color="#e2eadb" roughness={1} />
        </mesh>
        <Grid
          args={[R * 8, R * 8]}
          position={[0, 0.005, 0]}
          cellSize={10}
          cellThickness={0.6}
          cellColor="#cdd8c6"
          sectionSize={50}
          sectionThickness={1}
          sectionColor="#b6c4ae"
          fadeDistance={R * 6}
          fadeStrength={1.5}
        />
        <PlotMesh
          ring={ring}
          growth={growth}
          selected={selected?.kind === 'plot'}
          onSelect={() => setSelected({ kind: 'plot' })}
        />
        {layout.positions.length > 0 && (
          <Trees
            layout={layout}
            size={size}
            selectedIndex={selectedIndex}
            onSelect={(index) => setSelected({ kind: 'tree', index })}
          />
        )}
        {tree && (
          <Html
            position={[tree[0], treeTop, -tree[1]]}
            center
            distanceFactor={undefined}
            zIndexRange={[20, 0]}
          >
            <span className="whitespace-nowrap rounded-full bg-panel-dark px-2.5 py-1 text-[11px] font-semibold text-white shadow">
              {t('land3d.treeTitle', { n: (selectedIndex ?? 0) + 1 })}
            </span>
          </Html>
        )}
        <OrbitControls
          ref={controls as never}
          makeDefault
          enableDamping
          maxPolarAngle={Math.PI / 2.15}
          minDistance={R * 0.25}
          maxDistance={R * 5}
        />
      </Canvas>

      {/* KPI cards */}
      <div className="pointer-events-none absolute left-3 right-14 top-3 grid grid-cols-2 gap-2 2xl:grid-cols-4">
        <Kpi
          label={t('land3d.kpiTrees')}
          value={formatNumber(treeCount, locale, { maximumFractionDigits: 0 })}
          sub={t('land3d.kpiTreesSub', {
            density: Math.round(treeCount / Math.max(areaHectares, 0.0001)),
          })}
        />
        <Kpi
          label={t('land3d.kpiAge')}
          value={String(age)}
          sub={t('land3d.kpiAgeSub', { year: standYear })}
        />
        <Kpi
          label={t('land3d.kpiAnnual')}
          value={carbon ? fmt(carbon.annual.central) : '—'}
          sub={t('land3d.kpiAnnualSub')}
        />
        <Kpi
          label={t('land3d.kpiCumulative')}
          value={carbon ? fmt(carbon.cumulative.central, 0) : '—'}
          sub={t('land3d.kpiCumulativeSub')}
        />
      </div>

      {/* View controls */}
      <div className="absolute right-3 top-3 flex flex-col overflow-hidden rounded-[10px] border border-line bg-white/95 shadow-sm">
        <button
          type="button"
          aria-label={t('land3d.zoomIn')}
          onClick={() => dolly(0.8)}
          className="flex h-9 w-9 items-center justify-center hover:bg-ground"
        >
          <Plus size={16} aria-hidden="true" />
        </button>
        <button
          type="button"
          aria-label={t('land3d.zoomOut')}
          onClick={() => dolly(1.25)}
          className="flex h-9 w-9 items-center justify-center border-t border-line hover:bg-ground"
        >
          <Minus size={16} aria-hidden="true" />
        </button>
        <button
          type="button"
          aria-label={t('land3d.resetView')}
          onClick={reset}
          className="flex h-9 w-9 items-center justify-center border-t border-line hover:bg-ground"
        >
          <RotateCcw size={15} aria-hidden="true" />
        </button>
      </div>

      {/* Selection card */}
      {selected && (
        <aside
          className="absolute right-14 top-[172px] z-30 w-[280px] 2xl:top-[92px] max-w-[calc(100%-4.5rem)] rounded-[14px] border border-line bg-white p-3.5 shadow-lg"
          aria-live="polite"
        >
          <div className="mb-2 flex items-start justify-between gap-2">
            <div>
              <span className="eyebrow text-forest-deep">
                {selected.kind === 'plot' ? t('land3d.plotTitle') : speciesName}
              </span>
              <h3 className="m-0 text-[16px]">
                {selected.kind === 'plot'
                  ? `${fmt(areaHectares, 2)} ha`
                  : t('land3d.treeTitle', { n: (selectedIndex ?? 0) + 1 })}
              </h3>
            </div>
            <button
              type="button"
              aria-label={t('land3d.close')}
              onClick={() => setSelected(null)}
              className="flex h-7 w-7 items-center justify-center rounded-full hover:bg-ground"
            >
              <X size={14} aria-hidden="true" />
            </button>
          </div>
          {selected.kind === 'plot' ? (
            <div>
              <Row label={t('land3d.plotArea')} value={`${fmt(areaHectares, 2)} ha`} />
              <Row
                label={t('land3d.plotTrees')}
                value={formatNumber(treeCount, locale, { maximumFractionDigits: 0 })}
              />
              <Row label={t('land3d.plotSpacing')} value={`${fmt(layout.spacing, 1)} m`} />
              <Row
                label={t('land3d.kpiCumulative')}
                value={
                  carbon
                    ? `${fmt(carbon.cumulative.low, 0)}–${fmt(carbon.cumulative.high, 0)} tCO₂e`
                    : '—'
                }
              />
              <p className="m-0 mt-2 text-[11.5px] leading-relaxed text-ink-2">
                {t('land3d.plotBoundary')}:{' '}
                {boundarySaved ? t('land3d.boundarySaved') : t('land3d.boundarySquare')}
              </p>
            </div>
          ) : (
            <div>
              <Row label={t('land3d.treeStatus')} value={stage} />
              <Row label={t('land3d.treeAge')} value={String(age)} />
              <Row
                label={t('land3d.treeHeight')}
                value={size.heightM === null ? '—' : `${fmt(size.heightM)} m`}
              />
              <Row
                label={t('land3d.treeCrown')}
                value={size.crownDiameterM === null ? '—' : `${fmt(size.crownDiameterM)} m`}
              />
              <Row
                label={t('land3d.treeAnnual')}
                value={carbon ? `${fmt(carbon.perTreeAnnualKg, 0)} kg CO₂e` : '—'}
              />
              <Row
                label={t('land3d.treeCumulative')}
                value={carbon ? `${fmt(carbon.perTreeCumulativeKg, 0)} kg CO₂e` : '—'}
              />
              <p className="m-0 mt-2 text-[11px] leading-relaxed text-muted">
                {t('land3d.perTreeNote')}{' '}
                {size.heightM === null
                  ? t('land3d.sizeMissing')
                  : t('land3d.sizeSource', { status: size.heightStatus ?? '—' })}
                {layout.treesPerDrawn > 1 && (
                  <>
                    {' '}
                    {t('land3d.drawnFor', {
                      n: formatNumber(layout.treesPerDrawn, locale, { maximumFractionDigits: 1 }),
                    })}
                  </>
                )}
              </p>
            </div>
          )}
          <p className="m-0 mt-2 rounded-[8px] bg-amber-tint px-2 py-1 text-[11px] font-semibold text-amber-text">
            {t('land3d.notCredit')}
          </p>
        </aside>
      )}

      {!selected && (
        <div className="pointer-events-none absolute bottom-3 left-3 flex flex-wrap gap-2 text-[11px]">
          <span className="rounded-full bg-white/90 px-2.5 py-1 text-ink-2 shadow-sm">
            {t('land3d.hint')}
          </span>
          <span className="rounded-full bg-white/90 px-2.5 py-1 text-ink-2 shadow-sm">
            {t('land3d.grid')}
          </span>
        </div>
      )}
    </div>
  );
}
