import { useState } from 'react';
import { ArrowDown, ArrowSquareOut, Cube, Database, Info, SpinnerGap, WarningCircle } from '@phosphor-icons/react';
import { categoryFor, imageLabels, safeLink, sourceLabels } from './labels.js';

export function Status({ resource }) {
  if (resource.loading) return <div className="state-panel" role="status"><SpinnerGap className="spinner" size={23} /> 正在载入档案…</div>;
  if (resource.error) return <div className="state-panel error" role="alert"><WarningCircle size={22} /> {resource.error}<button className="button small" onClick={resource.retry}>重试</button></div>;
  return null;
}

export function Empty({ children }) {
  return <div className="state-panel"><Database size={22} /> {children}</div>;
}

export function External({ href, children, className }) {
  const url = safeLink(href);
  return url ? <a className={className} href={url} target="_blank" rel="noopener noreferrer">{children}<ArrowSquareOut aria-hidden="true" size={15} /></a> : <span className={className}>{children}</span>;
}

export function SourceList({ sources = [], compact = false }) {
  if (!sources.length) return <p className="muted">暂未收录可定位的来源。</p>;
  return (
    <ul className={compact ? 'sources compact' : 'sources'}>
      {sources.map((source) => (
        <li key={source.id}>
          <span className="badge">{sourceLabels[source.type] || '来源'}</span>
          <div>
            <External className="inline-link" href={source.url}>{source.title}</External>
            {source.locator ? <small>{source.locator}</small> : null}
            {!compact && source.note ? <p>{source.note}</p> : null}
          </div>
        </li>
      ))}
    </ul>
  );
}

export function SourcesFor({ product, ids = [] }) {
  const sources = product.sources.filter((source) => ids.includes(source.id));
  if (!sources.length) return null;
  return <details className="field-sources"><summary><Info size={14} /> {sources.length} 条来源</summary><SourceList sources={sources} compact /></details>;
}

export function ProductVisual({ product, hero = false }) {
  const [failed, setFailed] = useState(false);
  const category = categoryFor(product.category);
  const Icon = category.icon;
  const graphic = product.image;
  const showImage = graphic?.url && !failed;
  return (
    <figure className={`product-visual theme-${product.category}${hero ? ' hero-image' : ''}`}>
      {showImage
        ? <img src={graphic.url} alt={graphic.alt || product.name} loading={hero ? 'eager' : 'lazy'} onError={() => setFailed(true)} />
        : <div className="product-art" aria-hidden="true"><span className="art-cross cross-top">+</span><Icon weight="thin" /><span className="art-cross cross-bottom">+</span><span>{category.english}</span></div>}
      <figcaption>{showImage ? imageLabels[graphic.type] || '参考图片' : '品类图标'}</figcaption>
    </figure>
  );
}

export function ModelBadge() {
  return <span className="badge accent"><Cube size={15} /> 3D 档案</span>;
}

export function JumpLink({ href, children }) {
  return <a className="button" href={href}><ArrowDown size={17} /> {children}</a>;
}
