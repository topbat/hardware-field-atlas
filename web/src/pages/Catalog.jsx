import { useState } from 'react';
import { sitePath } from '../deployment.js';
import { Link, useSearchParams } from 'react-router-dom';
import { ArrowDownRight, ArrowRight, ArrowUpRight, Check, Cube, Eyeglasses, GitDiff, MagnifyingGlass, Sliders, X } from '@phosphor-icons/react';
import { useResource } from '../api.js';
import { Empty, External, ModelBadge, ProductVisual, Status } from '../components.jsx';
import { categories, categoryFor, computeLabels, imageLabels, kindLabels, partLabels, photoSource, productPhotos } from '../labels.js';

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

function HeroVisual() {
  const flagship = useResource('/products/xiaomi-glasses');
  const [failed, setFailed] = useState(() => new Set());
  const concept = sitePath('/assets/atlas-hero.webp');
  const product = flagship.value;
  const photo = productPhotos(product).find((item) => !failed.has(item.url) && photoSource(product, item));
  const source = photoSource(product, photo);
  const imageUrl = photo?.url || (!flagship.loading && !failed.has(concept) ? concept : null);
  return (
    <figure className={`hero-visual${photo ? ' has-photo' : ''}`}>
      {imageUrl
        ? <img key={imageUrl} src={imageUrl} alt={photo?.alt || '智能眼镜的爆炸概念示意'} fetchPriority="high" referrerPolicy="no-referrer" onError={() => setFailed((urls) => new Set(urls).add(imageUrl))} />
        : <div className="hero-visual-fallback" aria-hidden="true"><Eyeglasses weight="thin" size={166} /></div>}
      <div className="hero-coordinate coordinate-left" aria-hidden="true">+</div>
      <div className="hero-coordinate coordinate-right" aria-hidden="true">+</div>
      <figcaption>
        {photo ? <Link className="inline-link" to={`/products/${product.id}`}>FIG. 01 / {product.name}</Link> : <span>FIG. 01 / 智能眼镜</span>}
        <span>{photo ? imageLabels[photo.type] : imageUrl ? '概念示意' : '品类图标'}{source ? <> · <External className="inline-link" href={source.url}>图片来源</External></> : null}</span>
      </figcaption>
    </figure>
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
  const apiParams = new URLSearchParams({ limit: '100' });
  for (const key of ['q', 'category', 'kind', 'compute', 'model']) {
    const value = params.get(key);
    if (value) apiParams.set(key, value);
  }
  const resource = useResource(`/catalog?${apiParams}`);
  const data = resource.value;
  const update = (key, value) => {
    setParams((current) => {
      const next = new URLSearchParams(current);
      if (value) next.set(key, value);
      else next.delete(key);
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
          <p>从产品到零件，从结构到证据。查找、比较和研究国内 AI 硬件与开源项目。</p>
          <SearchForm key={query} query={query} onSearch={search} />
          <div className="search-examples"><span>试着搜</span>{examples.map((example) => <button key={example} onClick={() => search(example)}>{example}<ArrowUpRight size={13} /></button>)}</div>
        </div>
        <HeroVisual />
      </section>
      <div className="wrap">
        <section className="categories" aria-label="按品类浏览">
          {categories.map(({ id, label, icon: Icon, english }, index) => (
            <button key={id} className={`category-button${category === id ? ' active' : ''}`} aria-pressed={category === id} onClick={() => update('category', category === id ? '' : id)}>
              <span className="category-index">{String(index + 1).padStart(2, '0')}</span>
              <Icon size={24} weight="light" aria-hidden="true" />
              <span className="category-text"><strong>{label}</strong><small>{english}</small></span>
              <ArrowDownRight size={15} aria-hidden="true" className="category-arrow" />
            </button>
          ))}
        </section>
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
        </section>
      </div>
    </>
  );
}
