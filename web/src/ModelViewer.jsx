import { useEffect, useRef, useState } from 'react';
import { ArrowCounterClockwise, ArrowsOutCardinal, Cube, EyeSlash, WarningCircle } from '@phosphor-icons/react';
import {
  AmbientLight, Box3, Color, DirectionalLight, Group, MathUtils, PerspectiveCamera,
  Raycaster, Scene, SRGBColorSpace, Vector2, Vector3, WebGLRenderer,
} from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

function disposeScene(root) {
  const geometries = new Set();
  const materials = new Set();
  const textures = new Set();
  root.traverse((node) => {
    if (!node.isMesh) return;
    geometries.add(node.geometry);
    for (const material of Array.isArray(node.material) ? node.material : [node.material]) {
      materials.add(material);
      for (const value of Object.values(material)) if (value?.isTexture) textures.add(value);
    }
  });
  for (const geometry of geometries) geometry.dispose();
  for (const material of materials) material.dispose();
  for (const texture of textures) {
    texture.source?.data?.close?.();
    texture.dispose();
  }
}

function createViewer(host, select, ids) {
  const renderer = new WebGLRenderer({ alpha: true, antialias: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.75));
  renderer.outputColorSpace = SRGBColorSpace;
  host.appendChild(renderer.domElement);
  const camera = new PerspectiveCamera(33, 1, 0.01, 150);
  const scene = new Scene();
  const contents = new Group();
  scene.add(contents, new AmbientLight(0xf4f0e8, 2.45));
  const key = new DirectionalLight(0xffffff, 3.0);
  key.position.set(3, 5, 4);
  const fill = new DirectionalLight(0xe5edff, 1.35);
  fill.position.set(-4, 1, -3);
  scene.add(key, fill);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = false;
  const render = () => renderer.render(scene, camera);
  controls.addEventListener('change', render);
  const resize = new ResizeObserver(() => {
    const { clientWidth, clientHeight } = host;
    if (!clientWidth || !clientHeight) return;
    renderer.setSize(clientWidth, clientHeight);
    camera.aspect = clientWidth / clientHeight;
    camera.updateProjectionMatrix();
    render();
  });
  resize.observe(host);
  const known = new Set(ids);
  const bindings = [];
  const raycastable = [];
  const boundMaterials = [];
  const accent = new Color('#ed653c');
  let sceneModel;
  let currentExplosion = 0;

  function partId(node) {
    for (let current = node; current && current !== contents; current = current.parent) {
      const id = current.userData.part_id || current.name;
      if (known.has(id)) return id;
    }
    return null;
  }

  function reset() {
    if (!sceneModel) return;
    const distance = 5.5 / Math.min(1, camera.aspect * 1.28);
    currentExplosion = 0;
    camera.position.set(distance * 0.62, distance * 0.45, distance * 0.7);
    controls.target.set(0, 0, 0);
    controls.minDistance = 1.1;
    controls.maxDistance = 16;
    controls.update();
    render();
  }

  function load(model) {
    sceneModel = model;
    const box = new Box3().setFromObject(model);
    const size = box.getSize(new Vector3());
    const center = box.getCenter(new Vector3());
    const maxSize = Math.max(size.x, size.y, size.z);
    if (!Number.isFinite(maxSize) || maxSize <= 0) throw new Error('无有效模型尺寸');
    const scale = 2.9 / maxSize;
    const wrapper = new Group();
    wrapper.scale.setScalar(scale);
    wrapper.position.copy(center).multiplyScalar(-scale);
    wrapper.add(model);
    contents.add(wrapper);
    contents.updateMatrixWorld(true);
    const originalMaterials = new Set();
    model.traverse((node) => {
      const id = partId(node);
      if (!id) return;
      if (partId(node.parent) !== id) {
        const supplied = node.userData.explode;
        const offset = new Vector3();
        if (Array.isArray(supplied) && supplied.length === 3 && supplied.every(Number.isFinite)) {
          offset.fromArray(supplied).multiplyScalar(1.42);
        } else {
          new Box3().setFromObject(node).getCenter(offset);
          if (offset.lengthSq() < 0.015) {
            const angle = 2 * Math.PI * bindings.length * 0.618;
            offset.set(Math.cos(angle), 0.25, Math.sin(angle));
          }
          offset.normalize().multiplyScalar(1.15);
        }
        const worldStart = node.getWorldPosition(new Vector3());
        const worldEnd = worldStart.clone().add(offset);
        const direction = node.parent.worldToLocal(worldEnd).sub(node.parent.worldToLocal(worldStart));
        bindings.push({ node, id, start: node.position.clone(), direction });
      }
      if (!node.isMesh) return;
      raycastable.push(node);
      const materials = Array.isArray(node.material) ? node.material : [node.material];
      const copies = materials.map((material) => {
        originalMaterials.add(material);
        const copy = material.clone();
        if (copy.emissive) boundMaterials.push({ id, copy, color: copy.emissive.clone(), intensity: copy.emissiveIntensity });
        return copy;
      });
      node.material = Array.isArray(node.material) ? copies : copies[0];
    });
    const liveMaterials = new Set();
    model.traverse((node) => {
      if (node.isMesh) for (const material of [].concat(node.material)) liveMaterials.add(material);
    });
    for (const original of originalMaterials) if (!liveMaterials.has(original)) original.dispose();
    reset();
    return new Set(bindings.map(({ id }) => id)).size;
  }

  function update({ exploded, active, hidden }) {
    if (exploded !== currentExplosion) {
      const factor = (1 + 0.18 * exploded) / (1 + 0.18 * currentExplosion);
      camera.position.sub(controls.target).multiplyScalar(factor).add(controls.target);
      currentExplosion = exploded;
    }
    for (const { node, id, start, direction } of bindings) {
      node.position.copy(start).addScaledVector(direction, exploded);
      node.visible = id !== hidden;
    }
    for (const { id, copy, color, intensity } of boundMaterials) {
      copy.emissive.copy(id === active ? accent : color);
      copy.emissiveIntensity = id === active ? 0.45 : intensity;
    }
    render();
  }

  let pointer;
  const pointerDown = (event) => { pointer = { x: event.clientX, y: event.clientY }; };
  const pointerUp = (event) => {
    if (!pointer || Math.hypot(event.clientX - pointer.x, event.clientY - pointer.y) > 5) return;
    const rect = renderer.domElement.getBoundingClientRect();
    const vector = new Vector2(2 * (event.clientX - rect.left) / rect.width - 1, 1 - 2 * (event.clientY - rect.top) / rect.height);
    const ray = new Raycaster();
    ray.setFromCamera(vector, camera);
    const hit = ray.intersectObjects(raycastable, false).find(({ object }) => {
      for (let current = object; current; current = current.parent) if (!current.visible) return false;
      return true;
    });
    if (hit) select(partId(hit.object));
  };
  renderer.domElement.addEventListener('pointerdown', pointerDown);
  renderer.domElement.addEventListener('pointerup', pointerUp);

  function destroy() {
    resize.disconnect();
    controls.removeEventListener('change', render);
    controls.dispose();
    renderer.domElement.removeEventListener('pointerdown', pointerDown);
    renderer.domElement.removeEventListener('pointerup', pointerUp);
    renderer.domElement.remove();
    disposeScene(contents);
    renderer.dispose();
  }

  return { load, reset, update, destroy };
}

export default function ModelViewer({ url, ids, active, onSelect }) {
  const host = useRef(null);
  const viewer = useRef(null);
  const callback = useRef(onSelect);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [bindingCount, setBindingCount] = useState(0);
  const [exploded, setExploded] = useState(0);
  const [hidden, setHidden] = useState(null);
  callback.current = onSelect;
  const idKey = ids.join(' ');
  useEffect(() => {
    let stopped = false;
    try {
      viewer.current = createViewer(host.current, (id) => callback.current(id), idKey.split(' '));
    } catch {
      setLoading(false);
      setError('浏览器暂时无法创建 3D 视图。请切换到部件示意图。');
      return undefined;
    }
    const instance = viewer.current;
    new GLTFLoader().loadAsync(url).then(({ scene }) => {
      if (stopped) {
        disposeScene(scene);
        return;
      }
      try {
        setBindingCount(instance.load(scene));
      } catch (error) {
        if (!scene.parent) disposeScene(scene);
        throw error;
      }
      setLoading(false);
    }).catch(() => {
      if (stopped) return;
      setLoading(false);
      setError('模型加载失败。请切换到部件示意图或重试。');
    });
    return () => {
      stopped = true;
      viewer.current = null;
      instance.destroy();
    };
  }, [url, idKey]);

  useEffect(() => {
    if (!loading && !error) viewer.current?.update({ exploded: MathUtils.clamp(exploded / 100, 0, 1), active, hidden });
  }, [exploded, active, hidden, loading, error]);

  return (
    <div className="viewer">
      <div className="viewer-stage">
        <div className="canvas-host" ref={host} aria-label="可旋转的部件 3D 模型" />
        <span className="viewer-axis"><ArrowsOutCardinal size={16} /> 3D 检视</span>
        {loading ? <div className="viewer-status" role="status"><Cube size={22} /> 模型载入中…</div> : null}
        {error ? <div className="viewer-status" role="alert"><WarningCircle size={22} /> {error}</div> : null}
      </div>
      <div className="viewer-toolbar">
        <label><span>展开结构</span><input type="range" min="0" max="100" value={exploded} disabled={!bindingCount || Boolean(error)} onChange={(event) => setExploded(Number(event.target.value))} /><span className="mono">{exploded}%</span></label>
        <button className="button small" disabled={loading || Boolean(error) || (!active && !hidden)} onClick={() => setHidden((current) => current ? null : active)}><EyeSlash size={17} /> {hidden ? '显示部件' : '隐藏所选'}</button>
        <button className="button small" disabled={loading || Boolean(error)} onClick={() => { setExploded(0); setHidden(null); viewer.current?.reset(); }}><ArrowCounterClockwise size={17} /> 复位</button>
      </div>
    </div>
  );
}
