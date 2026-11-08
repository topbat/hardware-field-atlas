import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ArrowLeft, ArrowUpRight, Flask, GitDiff, Plus, X } from '@phosphor-icons/react';
import { useResource } from '../api.js';
import { Empty, ProductVisual, SourcesFor, Status } from '../components.jsx';
import { categoryFor, computeLabels, kindLabels } from '../labels.js';

function stringList(values) {
  return values.length ? values.join('；') : '未收录';
}

function rowsFor(products) {
  const common = [
    { label: '品牌', value: (product) => product.brand },
    { label: '品类', value: (product) => categoryFor(product.category).label },
    { label: '档案类型', value: (product) => kindLabels[product.kind] },
    { label: '适用版本', value: (product) => product.revision },
    { label: 'AI 能力', value: (product) => stringList(product.abilities.map((item) => item.name)) },
    { label: '推理位置', value: (product) => stringList([...new Set(product.abilities.map((item) => computeLabels[item.compute]))]) },
    { label: '断网表现', value: (product) => stringList(product.abilities.map((item) => `${item.name}：${item.offline}`)), sources: (product) => product.abilities.flatMap((item) => item.sourceIds) },
    { label: '已收录部件', value: (product) => `${product.parts.length} 项` },
  ];
  const keys = new Map();
  for (const product of products) for (const spec of product.specs) if (!keys.has(spec.key)) keys.set(spec.key, spec.label);
  return [
    ...common,
    ...Array.from(keys, ([key, label]) => ({
      label,
      key,
      value: (product) => product.specs.find((item) => item.key === key)?.value || '未收录',
      sources: (product) => product.specs.find((item) => item.key === key)?.sourceIds || [],
    })),
  ];
}

export function Compare({ selection }) {
  const [params, setParams] = useSearchParams();
  const routeIds = params.get('ids');
  const ids = routeIds ? [...new Set(routeIds.split(',').filter((id) => /^[a-z0-9-]{1,80}$/.test(id)))].slice(0, 4) : selection.ids;
  const [differences, setDifferences] = useState(false);
  const [candidate, setCandidate] = useState('');
  const query = new URLSearchParams({ ids: ids.join(',') });
  const resource = useResource(ids.length >= 2 ? `/compare?${query}` : null);
  const options = useResource('/catalog?limit=100');
  const products = resource.value?.products || [];
  const rows = rowsFor(products).filter((row) => !differences || new Set(products.map(row.value)).size > 1);
  const available = (options.value?.products || []).filter((product) => !ids.includes(product.id));
  const labQuery = new URLSearchParams({ workflow: 'compare' });
  for (const id of ids) labQuery.append('product', id);

  function update(next) {
    selection.set(next);
    setParams(next.length ? { ids: next.join(',') } : {}, { replace: true });
  }

  return (
    <div className="wrap page-top compare-page">
      <Link className="inline-link breadcrumb" to="/"><ArrowLeft size={16} /> 硬件档案</Link>
      <div className="page-intro">
        <span className="eyebrow"><span className="signal-dot" /> BENCH / 02</span>
        <h1>把差异摊开看。</h1>
        <p>并排查看 2–4 款硬件的规格、推理位置和断网表现。</p>
      </div>
      <section className="surface compare-controls">
        <div className="picked-products">
          <GitDiff size={21} /><strong>对比台</strong><span className="mono">{ids.length}/4</span>
          {ids.map((id) => <button key={id} className="badge" onClick={() => update(ids.filter((item) => item !== id))} aria-label={`移除 ${options.value?.products.find((product) => product.id === id)?.name || id}`}>{options.value?.products.find((product) => product.id === id)?.name || id}<X size={14} /></button>)}
        </div>
        <form className="action-row" onSubmit={(event) => { event.preventDefault(); if (candidate && !ids.includes(candidate) && ids.length < 4) update([...ids, candidate]); setCandidate(''); }}>
          <label><span className="sr-only">选择要添加的产品</span><select value={candidate} disabled={ids.length >= 4 || options.loading} onChange={(event) => setCandidate(event.target.value)}><option value="">选择产品</option>{available.map((product) => <option key={product.id} value={product.id}>{product.name}</option>)}</select></label>
          <button type="submit" className="button small" disabled={!candidate || ids.length >= 4}><Plus size={17} /> 添加</button>
          <label className="check-filter"><input type="checkbox" checked={differences} onChange={(event) => setDifferences(event.target.checked)} /> 只看差异</label>
          {ids.length >= 2 ? <Link className="button small primary" to={`/research?${labQuery}`}><Flask size={17} /> 运行对比工作流</Link> : null}
        </form>
        <Status resource={options} />
      </section>
      <Status resource={resource} />
      {ids.length < 2 ? <Empty>选择至少两款硬件后开始对比。</Empty> : null}
      {products.length >= 2 ? (
        <div className="table-scroll compare-table" tabIndex={0} aria-label="横向滚动产品对比表">
          <table className="data-table">
            <thead><tr><th scope="col">对比项</th>{products.map((product) => (
              <th scope="col" key={product.id}><ProductVisual product={product} /><Link className="inline-link" to={`/products/${product.id}`}>{product.name}<ArrowUpRight size={17} /></Link></th>
            ))}</tr></thead>
            <tbody>{rows.map((row) => <tr key={row.key || row.label}><th scope="row">{row.label}</th>{products.map((product) => <td key={product.id}>{row.value(product)}{row.sources ? <SourcesFor product={product} ids={row.sources(product)} /> : null}</td>)}</tr>)}</tbody>
          </table>
          {!rows.length ? <Empty>已录入的项目没有差异。</Empty> : null}
        </div>
      ) : null}
    </div>
  );
}
