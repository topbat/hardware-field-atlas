import { useState } from 'react';
import { useResource } from '../api.js';

const pageSize = 100;
const encode = encodeURIComponent;
const pretty = (value) => JSON.stringify(value, null, 2);

async function adminRequest(path, token, { method = 'GET', body, etag } = {}) {
  const headers = { Accept: 'application/json', Authorization: `Bearer ${token}` };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (etag) headers['If-Match'] = etag;
  const response = await fetch(`/api/admin${path}`, {
    method, headers, cache: 'no-store',
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const result = await response.json().catch(() => null);
  if (response.status === 401) throw new Error('管理令牌无效或编辑服务未配置。');
  if (!response.ok || result === null) {
    if (typeof result?.detail === 'string') throw new Error(result.detail);
    if (response.status === 422) throw new Error('数据未通过校验，请检查必填字段和来源引用。');
    throw new Error('编辑服务暂时无法完成此操作。');
  }
  return method === 'PUT' ? { product: result, etag: response.headers.get('ETag') } : result;
}

async function readProduct(id) {
  const response = await fetch(`/api/products/${encode(id)}`, { cache: 'no-store' });
  if (!response.ok) throw new Error('无法读取档案。');
  return { product: await response.json(), etag: response.headers.get('ETag') };
}

function safeLink(value) {
  try {
    const parsed = new URL(value);
    return ['https:', 'http:'].includes(parsed.protocol) ? parsed.href : null;
  } catch {
    return null;
  }
}

function displayTime(value) {
  const iso = (value || '').replace(' ', 'T');
  const date = new Date(/Z$|[+-]\d{2}:?\d{2}$/.test(iso) ? iso : `${iso}Z`);
  return Number.isNaN(date.valueOf()) ? value : date.toLocaleString('zh-CN');
}

export function Admin() {
  const catalog = useResource('/catalog?limit=100');
  const [token, setToken] = useState('');
  const [credential, setCredential] = useState('');
  const [reports, setReports] = useState(null);
  const [offset, setOffset] = useState(0);
  const [chosen, setChosen] = useState('');
  const [product, setProduct] = useState(null);
  const [etag, setEtag] = useState(null);
  const [draft, setDraft] = useState('');
  const [confirmation, setConfirmation] = useState(null);
  const [revisions, setRevisions] = useState(null);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const dirty = Boolean(product && draft !== pretty(product));
  const pending = reports?.filter((item) => item.status === 'pending') || [];

  async function operate(label, operation) {
    setBusy(label);
    setError('');
    setNotice('');
    try {
      await operation();
    } catch (failure) {
      setError(failure.message);
    } finally {
      setBusy('');
    }
  }

  async function loadReports(next, activeCredential = credential) {
    const result = await adminRequest(`/corrections?limit=${pageSize}&offset=${next}`, activeCredential);
    setOffset(next);
    setReports(result.corrections);
  }

  function connect(event) {
    event.preventDefault();
    const activeCredential = token.trim();
    if (!activeCredential) return;
    setCredential('');
    setReports(null);
    setRevisions(null);
    setConfirmation(null);
    operate('正在验证…', async () => {
      await loadReports(0, activeCredential);
      setCredential(activeCredential);
      setToken('');
      setNotice('已连接编辑台。');
    });
  }

  function disconnect() {
    if (dirty && !window.confirm('断开会话并放弃尚未保存的修改？')) return;
    setCredential('');
    setToken('');
    setReports(null);
    setRevisions(null);
    setConfirmation(null);
    setProduct(null);
    setDraft('');
    setChosen('');
    setNotice('');
    setError('');
  }

  function moderate(item, status) {
    operate('正在更新纠错…', async () => {
      const result = await adminRequest(`/corrections/${encode(item.id)}`, credential, {
        method: 'PATCH', body: { status },
      });
      setReports((current) => current.map((row) => row.id === result.id ? { ...row, status: result.status } : row));
      setNotice(status === 'accepted' ? '已采纳纠错。可在档案编辑中应用核实后的修改。' : '已忽略纠错。');
    });
  }

  function openProduct(id) {
    if (!id || (dirty && !window.confirm('放弃尚未保存的修改并载入档案？'))) return;
    operate('正在读取档案…', async () => {
      const result = await readProduct(id);
      setChosen(id);
      setProduct(result.product);
      setEtag(result.etag);
      setDraft(pretty(result.product));
      setRevisions(null);
      setConfirmation(null);
    });
  }

  function prepareSave(event) {
    event.preventDefault();
    setError('');
    setNotice('');
    try {
      const next = JSON.parse(draft);
      if (!next || Array.isArray(next) || typeof next !== 'object' || next.id !== product.id) {
        throw new Error('JSON 必须是完整档案对象，且 id 必须与所选档案一致。');
      }
      const keys = [...new Set([...Object.keys(product), ...Object.keys(next)])];
      const changed = keys.filter((key) => pretty(next[key]) !== pretty(product[key]));
      if (!changed.length) throw new Error('档案内容没有变更。');
      setConfirmation({ product: next, fields: changed });
    } catch (failure) {
      setError(failure instanceof SyntaxError ? 'JSON 格式有误，请检查逗号、引号和括号。' : failure.message);
    }
  }

  function save() {
    if (!confirmation) return;
    operate('正在保存档案…', async () => {
      const path = `/products/${encode(product.id)}`;
      if (!etag) throw new Error('档案版本缺失。请重新载入再保存。');
      const result = await adminRequest(path, credential, { method: 'PUT', body: confirmation.product, etag });
      setProduct(result.product);
      setEtag(result.etag);
      setDraft(pretty(result.product));
      setConfirmation(null);
      setRevisions(null);
      setNotice('档案已保存，旧版已存入修订记录。');
    });
  }

  function loadRevisions() {
    operate('正在读取修订记录…', async () => {
      const result = await adminRequest(`/products/${encode(product.id)}/revisions`, credential);
      setRevisions(result.revisions);
    });
  }

  return (
    <div className="wrap page-top research-main">
      <div className="page-intro">
        <span className="eyebrow"><span className="signal-dot" /> EDITORIAL / 04</span>
        <h1>目录编辑台</h1>
        <p>核对纠错、编辑现有硬件档案，查看修订前后的记录。</p>
      </div>
      <section className="surface" aria-labelledby="editorial-session">
        <h2 id="editorial-session">编辑会话</h2>
        {credential ? (
          <div className="action-row">
            <span>已连接</span>
            <button className="button small" type="button" disabled={Boolean(busy)} onClick={disconnect}>断开编辑会话</button>
          </div>
        ) : (
          <form className="form-stack" onSubmit={connect}>
            <label htmlFor="admin-token">管理令牌</label>
            <input id="admin-token" type="password" value={token} autoComplete="off" spellCheck={false} disabled={Boolean(busy)} onChange={(event) => setToken(event.target.value)} />
            <button className="button primary" type="submit" disabled={Boolean(busy) || !token.trim()}>连接编辑台</button>
          </form>
        )}
      </section>
      {busy || notice ? <p role="status">{busy || notice}</p> : null}
      {error ? <p role="alert" className="research-warning">{error}</p> : null}
      {credential ? (
        <>
          <section className="surface" aria-labelledby="editorial-queue">
            <h2 id="editorial-queue">待审核纠错</h2>
            <div className="action-row">
              <button className="button small" type="button" disabled={Boolean(busy)} onClick={() => operate('正在读取纠错…', () => loadReports(offset))}>刷新</button>
              {offset ? <button className="button small" type="button" disabled={Boolean(busy)} onClick={() => operate('正在读取纠错…', () => loadReports(offset - pageSize))}>较新记录</button> : null}
              {reports?.length === pageSize ? <button className="button small" type="button" disabled={Boolean(busy)} onClick={() => operate('正在读取纠错…', () => loadReports(offset + pageSize))}>较早记录</button> : null}
            </div>
            {!pending.length ? <p>本页没有待审核纠错。</p> : (
              <ul className="notes-list">
                {pending.map((item) => {
                  const source = safeLink(item.url);
                  const name = catalog.value?.products.find(({ id }) => id === item.productId)?.name || item.productId;
                  return (
                    <li key={item.id}>
                      <strong>{name} · {item.field}</strong>
                      <p>{item.message}</p>
                      <small>{displayTime(item.createdAt)}</small>
                      {source ? <p><a className="inline-link" href={source} target="_blank" rel="noreferrer">查看提交的来源</a></p> : null}
                      <div className="action-row">
                        <button className="button small" type="button" disabled={Boolean(busy)} onClick={() => openProduct(item.productId)}>载入档案</button>
                        <button className="button small primary" type="button" disabled={Boolean(busy)} onClick={() => moderate(item, 'accepted')}>采纳</button>
                        <button className="button small" type="button" disabled={Boolean(busy)} onClick={() => moderate(item, 'dismissed')}>忽略</button>
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>
          <section className="surface" aria-labelledby="editorial-record">
            <h2 id="editorial-record">编辑档案</h2>
            <form className="form-stack" onSubmit={(event) => { event.preventDefault(); openProduct(chosen); }}>
              <label htmlFor="editorial-product">选择现有产品</label>
              <select id="editorial-product" value={chosen} disabled={Boolean(busy)} onChange={(event) => setChosen(event.target.value)}>
                <option value="">请选择产品</option>
                {catalog.value?.products.map(({ id, name }) => <option key={id} value={id}>{name}</option>)}
              </select>
              {catalog.error ? <p role="alert">{catalog.error} <button className="text-button" type="button" onClick={catalog.retry}>重试</button></p> : null}
              <button className="button small" type="submit" disabled={Boolean(busy) || !chosen}>载入档案</button>
            </form>
            {product ? (
              <>
                <form className="form-stack" onSubmit={prepareSave}>
                  <label htmlFor="editorial-draft">{product.name} · {product.id}</label>
                  <textarea id="editorial-draft" rows={20} value={draft} wrap="off" spellCheck={false} disabled={Boolean(busy)} onChange={(event) => { setDraft(event.target.value); setConfirmation(null); }} />
                  {confirmation ? (
                    <div>
                      <p>将更新「{product.name}」的字段：{confirmation.fields.join('、')}。旧版会保存为快照。</p>
                      <div className="action-row">
                        <button className="button primary" type="button" disabled={Boolean(busy)} onClick={save}>确认保存</button>
                        <button className="button" type="button" disabled={Boolean(busy)} onClick={() => setConfirmation(null)}>继续编辑</button>
                      </div>
                    </div>
                  ) : <button className="button primary" type="submit" disabled={Boolean(busy) || !dirty}>检查并预览修改</button>}
                </form>
                <h3>修订记录</h3>
                <button className="button small" type="button" disabled={Boolean(busy)} onClick={loadRevisions}>查看修订记录</button>
                {revisions?.length === 0 ? <p>暂时没有修订记录。</p> : null}
                {revisions?.map((record) => (
                  <details key={record.id}>
                    <summary>修订 #{record.id} · {displayTime(record.createdAt)}</summary>
                    <div className="form-stack">
                      <label>修改前<textarea rows={10} value={pretty(record.previous)} wrap="off" readOnly /></label>
                      <label>修改后<textarea rows={10} value={pretty(record.current)} wrap="off" readOnly /></label>
                    </div>
                  </details>
                ))}
              </>
            ) : null}
          </section>
        </>
      ) : null}
    </div>
  );
}
