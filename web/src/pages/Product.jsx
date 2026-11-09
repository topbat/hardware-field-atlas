import { lazy, Suspense, useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { ArrowLeft, ArrowRight, ArrowUpRight, Check, Circuitry, Cube, DownloadSimple, Flask, GitDiff, ImageSquare, ListBullets, Target, WarningCircle } from '@phosphor-icons/react';
import { request, useResource } from '../api.js';
import { Empty, External, ModelBadge, ProductVisual, SourceList, SourcesFor, Status } from '../components.jsx';
import { categoryFor, computeLabels, imageLabels, kindLabels, modelLabels, partLabels, photoSource, productPhotos, researchUrl } from '../labels.js';

const ModelViewer = lazy(() => import('../ModelViewer.jsx'));
const diagramIds = new Set(['xiaomi-glasses', 'xiaozhi-esp32', 'xiaomi-speaker-pro']);
const challenges = {
  'xiaomi-glasses': { answer: 'battery', choices: ['board', 'battery', 'camera'], question: '右镜腿里，哪个部件储存电能？' },
  'xiaozhi-esp32': { answer: 'mic', choices: ['display', 'speaker', 'mic'], question: '你说出唤醒词时，哪个部件先采集声音？' },
  'xiaomi-speaker-pro': { answer: 'radiators', choices: ['top', 'radiators', 'board'], question: '哪个部件借助音腔内的气压振动？' },
};

function PartChallenge({ product, onSelect }) {
  const [guess, setGuess] = useState(null);
  const challenge = challenges[product.id];
  if (!challenge) return null;
  const choices = challenge.choices.map((id) => product.parts.find((part) => part.id === id));
  if (choices.some((part) => !part)) return null;
  return (
    <details className="part-challenge">
      <summary><Target size={20} /> 拆解小挑战</summary>
      <p>{challenge.question}</p>
      <div className="action-row">{choices.map((part) => <button className={`button small${guess === part.id ? ' selected' : ''}`} key={part.id} aria-pressed={guess === part.id} onClick={() => { setGuess(part.id); onSelect(part.id); }}>{part.name}</button>)}</div>
      {guess ? <p role="status" className={guess === challenge.answer ? 'success-text' : 'muted'}>{guess === challenge.answer ? '找到了。部件详情里可以查证依据。' : '先看看刚选部件的用途，再试一次。'}</p> : null}
    </details>
  );
}

function PartDiagram({ product, active, onSelect }) {
  const url = `/assets/diagrams/${product.id}.svg`;
  const [pins, setPins] = useState([]);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    fetch(url, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error('missing diagram');
        return response.text();
      })
      .then((value) => {
        const svg = new DOMParser().parseFromString(value, 'image/svg+xml').documentElement;
        if (svg.localName !== 'svg') return;
        const [left, top, width, height] = (svg.getAttribute('viewBox') || '').split(/\s+/).map(Number);
        if (!width || !height) return;
        setPins(Array.from(svg.querySelectorAll('[data-part-id]'), (pin) => {
          const circle = pin.querySelector('circle');
          const x = 100 * (Number(circle?.getAttribute('cx')) - left) / width;
          const y = 100 * (Number(circle?.getAttribute('cy')) - top) / height;
          return { id: pin.getAttribute('data-part-id'), x, y, label: pin.querySelector('text')?.textContent };
        }).filter(({ id, x, y, label }) => id && label && x >= 0 && x <= 100 && y >= 0 && y <= 100));
      }).catch(() => {
        // The parts list continues to provide a keyboard-accessible selection.
      });
    return () => controller.abort();
  }, [url]);
  if (failed) return null;
  return (
    <figure className="part-diagram">
      <div className="part-diagram-frame">
        <img src={url} alt={`${product.name}结构与部件索引`} onError={() => setFailed(true)} />
        {pins.map((pin) => {
          const part = product.parts.find(({ id }) => id === pin.id);
          if (!part) return null;
          return <button className="diagram-pin" key={pin.id} style={{ left: `${pin.x}%`, top: `${pin.y}%` }} aria-label={`定位${part.name}`} aria-pressed={active === pin.id} onClick={() => onSelect(pin.id)}>{pin.label}</button>;
        })}
      </div>
      <figcaption>点击图中编号查看对应部件。形状与比例为示意。</figcaption>
    </figure>
  );
}

function Schematic({ product, active, onSelect }) {
  return (
    <div className="schematic">
      <div className="schematic-header"><Circuitry size={22} /><span>部件关系示意</span><small>示意图 / 位置与比例仅供参考</small></div>
      {diagramIds.has(product.id) ? <PartDiagram product={product} active={active} onSelect={onSelect} /> : null}
      {product.parts.length ? (
        <div className="schematic-grid">
          {product.parts.map((part, index) => (
            <button key={part.id} className={active === part.id ? 'active' : ''} aria-pressed={active === part.id} onClick={() => onSelect(part.id)}>
              <span className="schematic-id">{String(index + 1).padStart(2, '0')}</span>
              <strong>{part.name}</strong><small>{part.mpn || partLabels[part.status]}</small><ArrowUpRight size={16} />
            </button>
          ))}
        </div>
      ) : <ProductVisual product={product} />}
    </div>
  );
}

function PhotoGallery({ product, photos }) {
  const [selectedUrl, setSelectedUrl] = useState(null);
  const [failed, setFailed] = useState(() => new Set());
  const photo = photos.find(({ url }) => url === selectedUrl) || photos.find(({ url }) => !failed.has(url)) || photos[0];
  const source = photoSource(product, photo);
  const recordFailure = (url) => setFailed((urls) => new Set(urls).add(url));
  if (!photo) return <Empty>暂无已收录的产品或实物拆解照片。</Empty>;
  return (
    <section className="photo-gallery" aria-labelledby="photos-title">
      <div className="panel-heading">
        <div><h2 id="photos-title">产品与拆解照片</h2><p>核对外观、部件位置和照片对应的样机。</p></div>
        <span className="badge"><ImageSquare size={17} /> {photos.length} 张照片</span>
      </div>
      <div className={`photo-layout${photos.length === 1 ? ' single-photo' : ''}`}>
        <figure className="photo-main">
          <div className="photo-stage">
            {failed.has(photo.url)
              ? <div className="photo-unavailable" role="status"><ImageSquare size={30} /><p>暂时无法加载照片。</p>{source ? <External className="button small" href={source.url}>查看来源页面</External> : null}</div>
              : <img key={photo.url} src={photo.url} alt={photo.alt || product.name} referrerPolicy="no-referrer" onError={() => recordFailure(photo.url)} />}
          </div>
          <figcaption className="photo-caption">
            <span className="badge">{imageLabels[photo.type]}</span>
            <div>
              <strong>{photo.alt || product.name}</strong>
              {source ? <External className="inline-link" href={source.url}>{source.title}</External> : <small>图片来源待补</small>}
              {source?.locator ? <small>{source.locator}</small> : null}
            </div>
          </figcaption>
        </figure>
        {photos.length > 1 ? (
          <div className="photo-picks" aria-label="选择照片">
            {photos.map((item, index) => (
              <button key={item.url} type="button" className="photo-pick" aria-label={`查看第 ${index + 1} 张照片，${item.alt || imageLabels[item.type]}`} aria-pressed={photo.url === item.url} onClick={() => setSelectedUrl(item.url)}>
                {failed.has(item.url)
                  ? <div className="photo-thumb-fallback"><ImageSquare size={21} /></div>
                  : <img src={item.url} alt="" loading="lazy" referrerPolicy="no-referrer" onError={() => recordFailure(item.url)} />}
                <span><small className="mono">{String(index + 1).padStart(2, '0')} / {imageLabels[item.type]}</small><strong>{item.alt || product.name}</strong></span>
              </button>
            ))}
          </div>
        ) : null}
      </div>
    </section>
  );
}

function Cutaway({ product }) {
  const cutaway = product.cutaway;
  const [failed, setFailed] = useState(false);
  return (
    <figure className="cutaway-figure">
      <div className="asset-label"><span className="badge accent">{imageLabels[cutaway.type]}</span></div>
      {failed
        ? <Empty>暂时无法加载剖视图。</Empty>
        : <img src={cutaway.url} alt={cutaway.alt} referrerPolicy="no-referrer" onError={() => setFailed(true)} />}
      <figcaption className="photo-caption">
        <span className="badge">剖视图</span>
        <div><strong>{cutaway.alt}</strong>{cutaway.note ? <small>{cutaway.note}</small> : null}<SourcesFor product={product} ids={cutaway.sourceIds} /></div>
      </figcaption>
    </figure>
  );
}

const productImageTypes = [
  ['overview', '总体图', '完整外观和使用场景'],
  ['detail', '关键部位图', '关键外观、部件或功能细节'],
  ['specs', '硬件规格信息图', '已核验的参数与型号信息'],
  ['angles', '多角度图', '对照不同视角下的外形'],
];

function ProductImageGallery({ product }) {
  const { illustration } = product;
  const [failed, setFailed] = useState(() => new Set());
  const recordFailure = (key) => setFailed((items) => new Set(items).add(key));
  return (
    <section className="product-illustration" aria-labelledby="illustration-title">
      <div className="panel-heading">
        <div><h2 id="illustration-title">产品图解</h2><p>从完整外观到关键细节，每张图都可单独查看大图。</p></div>
        <span className="badge accent"><ImageSquare size={17} /> AI 生成配图</span>
      </div>
      <div className="product-image-grid">
        {productImageTypes.map(([key, title, description], index) => {
          const url = illustration.panels[key];
          return (
            <figure className={`product-image-panel panel-${key}`} key={key}>
              <figcaption>
                <div><span className="mono">0{index + 1}</span><h3>{title}</h3><p>{description}</p></div>
                {!failed.has(key) && <a href={url} target="_blank" rel="noopener" className="button small" aria-label={`打开${title}大图`}>大图 <ArrowUpRight size={15} /></a>}
              </figcaption>
              {failed.has(key) ? <Empty>暂时无法加载此图。</Empty> : (
                <a href={url} target="_blank" rel="noopener" aria-label={`查看${product.name}${title}`}>
                  <img src={url} alt={`${product.name} · ${title}`} loading={key === 'overview' ? 'eager' : 'lazy'} onError={() => recordFailure(key)} />
                </a>
              )}
            </figure>
          );
        })}
      </div>
      <div className="illustration-caption product-image-sources">
        <p>{illustration.exterior === 'concept' ? '外观为同类设备概念示意，准确型号外形待核对。' : '外观按公开资料重绘，比例和细节为近似。'}{illustration.technical === 'teardown' ? '部件关系以实物拆解来源为准。' : '关键部位图仅展示公开可见特征和功能。'}规格信息图使用已核验资料排版。</p>
        <SourcesFor product={product} ids={illustration.sourceIds} />
      </div>
    </section>
  );
}

function Illustration({ product }) {
  const { illustration } = product;
  const [failed, setFailed] = useState(false);
  const technical = illustration.technical === 'teardown' ? '拆解示意' : '功能分区';
  const concept = illustration.exterior === 'concept';
  return (
    <section className="product-illustration" aria-labelledby="illustration-title">
      <div className="panel-heading">
        <div><h2 id="illustration-title">产品图解</h2><p>一张图查看产品概览、不同视角和{technical}。</p></div>
        <span className="badge accent"><ImageSquare size={17} /> AI 生成示意</span>
      </div>
      <figure className="cutaway-figure illustration-figure">
        {failed
          ? <Empty>暂时无法加载产品图解。</Empty>
          : <a className="illustration-image" href={illustration.url} target="_blank" rel="noopener" aria-label="在新标签中查看产品图解大图">
              <img src={illustration.url} alt={`${product.name}的产品概览、不同视角和${technical}，AI 生成示意`} onError={() => setFailed(true)} />
            </a>}
        <figcaption className="photo-caption">
          <div className="illustration-caption">
            <div className="detail-tags"><span className="badge">产品介绍</span><span className="badge">多角度</span><span className="badge">{technical}</span></div>
            <small>{concept ? '外观为同类设备概念示意，准确型号外形待核对。' : '外观依公开资料绘制，比例和细节为近似。'}{illustration.technical === 'functional' ? '功能分区表示用途，内部装配未核实。' : '部件关系以实物拆解来源为准。'}</small>
            <SourcesFor product={product} ids={illustration.sourceIds} />
          </div>
          {!failed ? <a className="button small" href={illustration.url} target="_blank" rel="noopener"><ArrowUpRight size={15} /> 查看大图</a> : null}
        </figcaption>
      </figure>
    </section>
  );
}

function PartInspector({ product, part }) {
  if (!part) return <div className="part-inspector"><span className="eyebrow"><span className="signal-dot" /> COMPONENT</span><h3>部件详情</h3><p className="muted">在结构图、模型或物料清单中选择一个部件。</p></div>;
  return (
    <div className="part-inspector">
      <span className="eyebrow"><span className="signal-dot" /> COMPONENT</span>
      <h3>{part.name}</h3>
      <span className={`badge ${part.status === 'observed' ? 'accent' : ''}`}>{partLabels[part.status]}</span>
      <p>{part.role}</p>
      <dl className="part-facts">
        <div><dt>料号</dt><dd>{part.mpn ? <Link to={`/?q=${encodeURIComponent(part.mpn)}`} className="inline-link mono">{part.mpn}<ArrowUpRight size={14} /></Link> : '未公开'}</dd></div>
        <div><dt>制造商</dt><dd>{part.manufacturer || '未公开'}</dd></div>
        <div><dt>数量</dt><dd>{part.quantity || '待核验'}</dd></div>
        {part.sample ? <div><dt>适用样机</dt><dd>{part.sample}</dd></div> : null}
      </dl>
      <SourceList compact sources={product.sources.filter((source) => part.sourceIds.includes(source.id))} />
      <Link className="button small" to={researchUrl(product.id, part.id)}><Flask size={16} /> 研究此部件</Link>
    </div>
  );
}

function Structure({ product, part, select }) {
  const [view, setView] = useState(() => part && product.model ? '3d' : '2d');
  return (
    <>
      <div className="panel-heading">
        <div><h2>结构检视台</h2><p>{view === '3d' ? product.model?.note : '查看部件位置、结构和来源。'}</p></div>
        <div className="segmented" aria-label="结构视图">
          <button aria-pressed={view === '2d'} onClick={() => setView('2d')}><Circuitry size={17} /> 2D 部件</button>
          {product.cutaway ? <button aria-pressed={view === 'cutaway'} onClick={() => setView('cutaway')}><ImageSquare size={17} /> 剖视图</button> : null}
          {product.model ? <button aria-pressed={view === '3d'} onClick={() => setView('3d')}><Cube size={17} /> 3D 模型</button> : null}
        </div>
      </div>
      <div className="structure-layout">
        <div className="structure-graphic">
          {view === '3d' && product.model ? (
            <>
              <div className="asset-label"><span className="badge accent">{modelLabels[product.model.type]}</span></div>
              <Suspense fallback={<Empty>正在准备 3D 检视台…</Empty>}><ModelViewer url={product.model.url} ids={product.parts.map(({ id }) => id)} active={part?.id} onSelect={select} /></Suspense>
              {product.parts.length ? <div className="parts-index" aria-label="模型部件">{product.parts.map((item) => <button key={item.id} className={part?.id === item.id ? 'active' : ''} aria-pressed={part?.id === item.id} onClick={() => select(item.id)}>{item.name}</button>)}</div> : null}
            </>
          ) : view === 'cutaway' && product.cutaway
            ? <Cutaway product={product} />
            : <Schematic product={product} active={part?.id} onSelect={select} />}
        </div>
        <PartInspector product={product} part={part} />
      </div>
      <PartChallenge product={product} onSelect={select} />
    </>
  );
}

function Specs({ product }) {
  return (
    <div className="specs-layout">
      <section className="surface">
        <h2>规格</h2>
        {!product.specs.length ? <Empty>暂无可核验的规格。</Empty> : <dl className="spec-list">{product.specs.map((spec) => <div key={spec.key}><dt>{spec.label}</dt><dd>{spec.value}<SourcesFor product={product} ids={spec.sourceIds} /></dd></div>)}</dl>}
      </section>
      <section className="surface">
        <h2>AI 能力与断网表现</h2>
        {!product.abilities.length ? <Empty>暂无可核验的 AI 能力资料。</Empty> : product.abilities.map((ability) => (
          <article key={ability.name} className="ability">
            <div><h3>{ability.name}</h3><span className="badge accent">{computeLabels[ability.compute] || '待核验'}</span></div>
            <dl>
              <div><dt>输入</dt><dd>{ability.input}</dd></div>
              <div><dt>输出</dt><dd>{ability.output}</dd></div>
              <div><dt>断网表现</dt><dd>{ability.offline}</dd></div>
            </dl>
            <SourcesFor product={product} ids={ability.sourceIds} />
          </article>
        ))}
      </section>
    </div>
  );
}

function Bom({ product, part, select, showStructure }) {
  return (
    <>
      <div className="panel-heading">
        <div><h2>物料清单</h2><p>{product.parts.length} 条部件记录。型号、样机与核验状态分别保存。</p></div>
        <a className="button" href={`/api/products/${encodeURIComponent(product.id)}/bom.csv`}><DownloadSimple size={17} /> 导出 CSV</a>
      </div>
      {product.parts.length ? <div className="structure-layout bom-layout">
        <div className="table-scroll" tabIndex={0} aria-label="横向滚动物料清单">
          <table className="data-table">
            <thead><tr><th>部件</th><th>料号</th><th>数量</th><th>证据状态</th></tr></thead>
            <tbody>{product.parts.map((item) => (
              <tr key={item.id} className={part?.id === item.id ? 'active' : ''}>
                <th scope="row"><button className="text-button" aria-pressed={part?.id === item.id} onClick={() => select(item.id)}>{item.name}</button>{item.sample ? <small>{item.sample}</small> : null}</th>
                <td className="mono">{item.mpn || '—'}</td><td>{item.quantity || '—'}</td><td><span className="badge">{partLabels[item.status]}</span></td>
              </tr>
            ))}</tbody>
          </table>
        </div>
        <div><PartInspector product={product} part={part} />{part ? <button className="button small bom-jump" onClick={showStructure}><Cube size={16} /> 在结构中查看</button> : null}</div>
      </div> : <Empty>暂无公开的部件记录。</Empty>}
    </>
  );
}

function Correction({ product, part }) {
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [busy, setBusy] = useState(false);
  async function submit(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const fields = new FormData(form);
    setBusy(true);
    setError('');
    setSuccess('');
    try {
      const result = await request('/corrections', { method: 'POST', body: { productId: product.id, field: String(fields.get('field')).trim(), message: String(fields.get('message')).trim(), url: String(fields.get('url')).trim() || undefined } });
      setSuccess(`已提交审核 · ${result.id}`);
      form.reset();
    } catch (error) {
      setError(error.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <details className="correction">
      <summary><WarningCircle size={17} /> 提交资料纠错</summary>
      <form onSubmit={submit} className="form-stack">
        <label>有误的字段<input key={part?.id || 'product'} name="field" required defaultValue={part?.name || ''} placeholder="例如：主控芯片、样机版本" maxLength={100} /></label>
        <label>补充说明<textarea name="message" required maxLength={1500} rows={3} placeholder="描述你发现的差异。" /></label>
        <label>参考来源（选填）<input name="url" type="url" placeholder="https://…" maxLength={1000} /></label>
        <button className="button primary" type="submit" disabled={busy}>{busy ? '提交中…' : '提交审核'} <ArrowRight size={16} /></button>
        {error ? <p role="alert" className="error-text">{error}</p> : null}
        {success ? <p role="status">{success}</p> : null}
      </form>
    </details>
  );
}

const sections = [
  ['structure', '结构检视'], ['specs', '规格与 AI'], ['bom', '物料清单'], ['sources', '证据与来源'],
];

function ProductContent({ product, selection }) {
  const [params, setParams] = useSearchParams();
  const requestedTab = params.get('view');
  const part = product.parts.find((item) => item.id === params.get('part'));
  const photos = productPhotos(product);
  const tabs = [
    ...(photos.length || requestedTab === 'photos' ? [['photos', '实物照片']] : []),
    ...(product.illustration ? [['illustration', 'AI 图解']] : []),
    ...sections,
    ...(product.build ? [['build', '复现指南']] : []),
  ];
  const defaultTab = part ? 'structure' : photos.length ? 'photos' : product.illustration ? 'illustration' : 'structure';
  const tab = tabs.some(([value]) => value === requestedTab) ? requestedTab : defaultTab;
  const selected = selection.ids.includes(product.id);
  function setParameter(key, value) {
    setParams((current) => {
      const next = new URLSearchParams(current);
      next.set(key, value);
      return next;
    }, { replace: true });
  }
  const select = (id) => setParameter('part', id);
  const showTab = (value) => setParameter('view', value);

  return (
    <div className="wrap product-page">
      <Link className="inline-link breadcrumb" to="/"><ArrowLeft size={16} /> 硬件档案</Link>
      <section className="product-intro">
        <div>
          <div className="eyebrow"><span className="signal-dot" /> {categoryFor(product.category).english} / {product.brand}</div>
          <h1>{product.name}</h1>
          <p>{product.description || product.tagline}</p>
          <div className="detail-tags"><span className="badge">{kindLabels[product.kind]}</span>{product.model ? <ModelBadge /> : null}{product.tags.slice(0, 5).map((tag) => <span key={tag} className="badge">{tag}</span>)}</div>
          <div className="action-row">
            <Link className="button primary" to={researchUrl(product.id, part?.id)}><Flask size={18} /> 在研究室打开</Link>
            <button className={`button${selected ? ' selected' : ''}`} aria-pressed={selected} onClick={() => selection.toggle(product.id)} disabled={!selected && selection.ids.length >= 4}>{selected ? <Check size={18} /> : <GitDiff size={18} />} {selected ? '已加入对比' : '加入对比'}</button>
          </div>
        </div>
        <dl className="archive-meta"><div><dt>档案号</dt><dd>{product.id}</dd></div><div><dt>版本</dt><dd>{product.revision}</dd></div><div><dt>来源地区</dt><dd>{product.origin}</dd></div><div><dt>最近核验</dt><dd>{product.checkedAt}</dd></div></dl>
      </section>
      <nav className="tab-strip" aria-label="档案章节">
        {tabs.map(([id, label]) => <button key={id} className={id === tab ? 'active' : ''} aria-current={id === tab ? 'page' : undefined} onClick={() => showTab(id)}>{label}{id === 'photos' ? <span>{photos.length}</span> : id === 'bom' ? <span>{product.parts.length}</span> : null}</button>)}
      </nav>
      <section className="product-panel">
        {tab === 'photos' ? <PhotoGallery product={product} photos={photos} /> : null}
        {tab === 'illustration' ? product.illustration.panels ? <ProductImageGallery product={product} /> : <Illustration product={product} /> : null}
        {tab === 'structure' ? <Structure product={product} part={part} select={select} /> : null}
        {tab === 'specs' ? <Specs product={product} /> : null}
        {tab === 'bom' ? <Bom product={product} part={part} select={select} showStructure={() => showTab('structure')} /> : null}
        {tab === 'sources' ? <section className="surface"><h2>证据与来源</h2><SourceList sources={product.sources} /></section> : null}
        {tab === 'build' && product.build ? <section className="surface"><h2>复现指南</h2><p>{product.build.note}</p><ol className="build-steps">{product.build.steps.map((step, index) => <li key={index}>{step}</li>)}</ol><div className="action-row"><External className="button" href={product.build.repo}>打开源项目</External><Link className="button" to={researchUrl(product.id, undefined, 'build')}><ListBullets size={17} /> 生成复现清单</Link></div></section> : null}
      </section>
      <Correction product={product} part={part} />
    </div>
  );
}

export function Product({ selection }) {
  const { id } = useParams();
  const resource = useResource(`/products/${encodeURIComponent(id)}`);
  return resource.value ? <ProductContent key={id} product={resource.value} selection={selection} /> : <div className="wrap page-top"><Status resource={resource} /><Link className="inline-link" to="/"><ArrowLeft size={15} /> 返回档案</Link></div>;
}
