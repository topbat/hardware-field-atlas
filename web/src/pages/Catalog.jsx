import { useState } from 'react';
import { sitePath } from '../deployment.js';
import { Link, useSearchParams } from 'react-router-dom';
import { ArrowRight, ArrowUpRight, Check, Cube, GitDiff, MagnifyingGlass, Sliders, X } from '@phosphor-icons/react';
import { useResource } from '../api.js';
import { Empty, ModelBadge, ProductVisual, Status } from '../components.jsx';
import { categoryFor, computeLabels, kindLabels, partLabels } from '../labels.js';

import '../catalog-discovery.css';

const examples = ['ESP32-S3', 'BES2700H', '小米 AI 眼镜'];

function SearchForm({ query, onSearch }) {
  const [draft, setDraft] = useState(query);
  return (
    <form className="search-form" role="search" onSubmit={(event) => { event.preventDefault(); onSearch(draft.trim()); }}>
      <MagnifyingGlass size={23} aria-hidden="true" />
      <label className="sr-only" htmlFor="catalog-search">搜索产品、品牌或料号</label>
      <input id="catalog-search" value={draft} onChange={(event) => setDraft(event.target.value)} type="search" placeholder="搜产品、品牌或零件料号" maxLength={120} />
      <button className="button primary" type="submit">搜索 <ArrowRight size={17} /></button>
    </form>
  );
}

const scenes = [
  { label: '随身与出行', categories: ['phone', 'wearable', 'earbuds', 'glasses', 'vehicle', 'imaging', 'xr'] },
  { label: '家居与生活', categories: ['vacuum', 'security', 'speaker', 'mirror', 'toy', 'pet', 'outdoor', 'cabinet'] },
  { label: '办公与学习', categories: ['computer', 'tablet', 'recorder', 'education', 'desk'] },
  { label: '研发与拆解', categories: ['edge', 'fabrication', 'glasses', 'speaker', 'toy', 'computer'] },
];

function HeroVisual() {
  return (
    <figure className="hero-visual">
      <Link to="/products/xiaomi-glasses?view=structure" aria-label="拆开一副 AI 眼镜，查看 3D 结构">
        <img src={sitePath('/assets/atlas-hero.webp')} alt="智能眼镜分离镜腿、主板和电池的概念示意" fetchPriority="high" />
      </Link>
      <div className="hero-coordinate coordinate-left" aria-hidden="true">+</div>
      <div className="hero-coordinate coordinate-right" aria-hidden="true">+</div>
      <figcaption><Link className="inline-link" to="/products/xiaomi-glasses?view=structure">拆开一副 AI 眼镜 <ArrowUpRight size={14} /></Link><span>概念示意</span></figcaption>
    </figure>
  );
}

function SceneBrowser({ category, selectCategory, counts }) {
  const [sceneIndex, setSceneIndex] = useState(null);
  const matchedScene = scenes.findIndex((scene) => scene.categories.includes(category));
  const currentScene = scenes[sceneIndex];
  const active = currentScene && (!category || currentScene.categories.includes(category))
    ? sceneIndex : Math.max(0, matchedScene);
  return (
    <section className="scene-browser" aria-labelledby="scene-title">
      <div className="scene-header"><h2 id="scene-title">你想了解哪类硬件？</h2><span className="mono">BROWSE BY USE</span></div>
      <div className="scene-tabs" aria-label="按使用场景浏览">
        {scenes.map((scene, index) => (
          <button type="button" key={scene.label} aria-pressed={active === index} onClick={() => {
            setSceneIndex(index);
            if (category && !scene.categories.includes(category)) selectCategory('');
          }}>{scene.label}</button>
        ))}
      </div>
      <div className="scene-options" aria-label="按品类筛选">
        <button type="button" aria-pressed={!category} onClick={() => selectCategory('')}>全部品类</button>
        {scenes[active].categories.map((id) => {
          const { icon: Icon, label } = categoryFor(id);
          const count = counts?.find((item) => item.id === id)?.count;
          return <button type="button" key={id} aria-pressed={category === id} onClick={() => selectCategory(category === id ? '' : id)}>
            <Icon size={17} aria-hidden="true" />{label}{count != null && <small>{count}</small>}
          </button>;
        })}
      </div>
      {active === 3 && <div className="scene-tools">
        <Link className="button small primary" to="/products/esp32-s3-devkitc-1?view=engineering">打开 ESP32-S3 PCB 工作台 <ArrowUpRight size={14} /></Link>
        <Link className="button small" to="/?model=true"><Cube size={16} /> 浏览可拆解模型</Link>
        <Link className="button small" to="/research?workflow=build">打开复现工作流 <ArrowUpRight size={14} /></Link>
      </div>}
    </section>
  );
}

const stories = [
  { id: 'xiaomi-17-ultra', label: '随身 AI', title: '手机里的 AI 怎么工作？', view: 'specs' },
  { id: 'xiaozhi-esp32', label: '研发入门', title: '从一块板做起', view: 'structure' },
  { id: 'xiaomi-speaker-pro', label: '拆解笔记', title: '一个音箱里有什么？', view: 'illustration' },
];

function FeaturedStories({ products }) {
  const visible = stories.map((story) => ({ ...story, product: products.find(({ id }) => id === story.id) }))
    .filter(({ product }) => product);
  if (!visible.length) return null;
  return (
    <section className="feature-shelf" aria-labelledby="feature-title">
      <div className="scene-header"><h2 id="feature-title">从三个问题逛起</h2><span className="mono">FIELD NOTES</span></div>
      <div className="feature-grid">
        {visible.map(({ product, id, label, title, view }) => (
          <Link className="feature-story" key={id} to={'/products/' + id + '?view=' + view}>
            <ProductVisual product={product} />
            <div><span className="eyebrow">{label}</span><h3>{title} <ArrowUpRight size={16} /></h3><p>{product.name}</p></div>
          </Link>
        ))}
      </div>
    </section>
  );
}

function ProductCard({ product, selection }) {
  const selected = selection.ids.includes(product.id);
  return (
    <article className="catalog-card">
      <Link className="card-image-link" to={`/products/${product.id}`} aria-label={`查看${product.name}档案`}>
        <ProductVisual product={product} />
      </Link>
      <div className="card-body">
        <div className="card-classification"><span className="mono">{categoryFor(product.category).label} / {product.brand}</span>{product.model ? <ModelBadge /> : null}</div>
        <h3><Link to={`/products/${product.id}`}>{product.name}<ArrowUpRight size={17} /></Link></h3>
        <p>{product.tagline || product.description}</p>
        <div className="card-actions">
          <span className="badge">{kindLabels[product.kind] || product.kind}</span>
          <button type="button" className={`button small${selected ? ' selected' : ''}`} onClick={() => selection.toggle(product.id)} disabled={!selected && selection.ids.length >= 4} aria-pressed={selected}>{selected ? <Check size={16} /> : <GitDiff size={16} />} {selected ? '已加入' : '加入对比'}</button>
        </div>
      </div>
    </article>
  );
}

export function Catalog({ selection }) {
  const [params, setParams] = useSearchParams();
  const query = params.get('q') || '';
  const category = params.get('category') || '';
  const kind = params.get('kind') || '';
  const compute = params.get('compute') || '';
  const model = params.get('model') === 'true';
  const filtered = Boolean(query || category || kind || compute || model);
  const pageSize = 12;
  const requestedPage = Number(params.get('page'));
  const page = Number.isSafeInteger(requestedPage) && requestedPage > 0 ? requestedPage : 1;
  const apiParams = new URLSearchParams({ limit: String(pageSize), offset: String((page - 1) * pageSize) });
  for (const key of ['q', 'category', 'kind', 'compute', 'model']) {
    const value = params.get(key);
    if (value) apiParams.set(key, value);
  }
  const resource = useResource(`/catalog?${apiParams}`);
  const data = resource.value;
  const lastPage = Math.max(1, Math.ceil((data?.total || 0) / pageSize));
  const featured = useResource(!filtered && page === 1 ? '/compare?ids=' + stories.map(({ id }) => id).join(',') : null);
  const update = (key, value) => {
    setParams((current) => {
      const next = new URLSearchParams(current);
      if (value) next.set(key, value);
      else next.delete(key);
      if (key !== 'page') next.delete('page');
      return next;
    });
  };
  const search = (value) => update('q', value);

  return (
    <>
      <section className={`wrap hero${filtered ? ' hero-compact' : ''}`}>
        <div className="hero-content">
          <div className="eyebrow"><span className="signal-dot" /> FIELD GUIDE / CHINA</div>
          <h1>打开硬件，<br />看见<span>里面。</span></h1>
          <p>手机如何在本地处理照片？扫地机器人靠什么避障？从日常用途出发，沿着硬件、结构和证据继续研究。</p>
          <SearchForm key={query} query={query} onSearch={search} />
          <div className="search-examples"><span>试着搜</span>{examples.map((example) => <button key={example} onClick={() => search(example)}>{example}<ArrowUpRight size={13} /></button>)}</div>
        </div>
        <HeroVisual />
      </section>
      <div className="wrap">
        <SceneBrowser category={category} selectCategory={(value) => update('category', value)} counts={data?.categories} />
        {featured.value && <FeaturedStories products={featured.value.products} />}
        <section className="catalog-section" aria-labelledby="catalog-title">
          <div className="section-heading">
            <div><span className="eyebrow"><span className="signal-dot" /> INDEX 01</span><h2 id="catalog-title">{query ? `“${query}”的搜索结果` : category ? categoryFor(category).label : '硬件档案'}</h2></div>
            {data ? <span className="mono result-total">{data.total} 份产品档案</span> : null}
          </div>
          <div className="filters">
            <span className="filter-label"><Sliders size={18} /> 筛选</span>
            <label><span className="sr-only">档案类型</span><select value={kind} onChange={(event) => update('kind', event.target.value)}><option value="">所有类型</option>{Object.entries(kindLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
            <label><span className="sr-only">推理位置</span><select value={compute} onChange={(event) => update('compute', event.target.value)}><option value="">所有推理位置</option>{Object.entries(computeLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
            <label className="check-filter"><input type="checkbox" checked={model} onChange={(event) => update('model', event.target.checked ? 'true' : '')} /><Cube size={16} /> 有 3D 模型</label>
            {filtered ? <button className="text-button" onClick={() => setParams({})}><X size={15} /> 清除筛选</button> : null}
          </div>
          <Status resource={resource} />
          {data?.parts?.length ? (
            <section className="parts-results" aria-labelledby="parts-results-title">
              <h3 id="parts-results-title">零件与料号 <span className="mono">/ {data.parts.length}</span></h3>
              {data.parts.map(({ productId, productName, part }) => (
                <Link key={`${productId}/${part.id}`} to={`/products/${productId}?part=${encodeURIComponent(part.id)}`}>
                  <span><strong>{part.name}</strong><small>{part.mpn || '料号未公开'}{part.manufacturer ? ` · ${part.manufacturer}` : ''}</small></span>
                  <span>{productName} <span className="badge">{partLabels[part.status]}</span></span><ArrowUpRight size={18} />
                </Link>
              ))}
            </section>
          ) : null}
          {data && !data.products.length ? <Empty>没有符合条件的产品。试试去掉一个筛选条件。</Empty> : null}
          {data?.products.length ? <div className="catalog-grid">{data.products.map((product) => <ProductCard key={product.id} product={product} selection={selection} />)}</div> : null}
          {data && (lastPage > 1 || page > 1) && <nav className="catalog-pagination" aria-label="目录分页">
            <button type="button" className="button small" disabled={page <= 1} onClick={() => update('page', String(Math.max(1, Math.min(page - 1, lastPage))))}>上一页</button>
            <span className="mono">第 {page} / {lastPage} 页</span>
            <button type="button" className="button small" disabled={page >= lastPage} onClick={() => update('page', String(page + 1))}>下一页</button>
          </nav>}
        </section>
      </div>
    </>
  );
}
