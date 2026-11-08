import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  ArrowLeft, ArrowRight, BookmarkSimple, CheckCircle, Circuitry, ClockCounterClockwise,
  Flask, GitDiff, ImageSquare, ListChecks, MagnifyingGlass, SpinnerGap, Trash, X,
} from '@phosphor-icons/react';
import { request, useResource } from '../api.js';
import { Empty, External, Status } from '../components.jsx';

const workflows = [
  { id: 'search', label: '搜集资料', description: '按型号、品牌和料号找相关档案。', example: '有哪些设备用了 ESP32-S3？', icon: MagnifyingGlass },
  { id: 'evidence', label: '证据查证', description: '追溯部件、规格和拆解来源。', example: '这个部件有哪些拆解证据？', icon: Circuitry },
  { id: 'compare', label: '架构对比', description: '核对推理位置、断网能力与差异。', example: '比较这些设备的断网能力和端云分工。', icon: GitDiff },
  { id: 'build', label: '复现清单', description: '整理开源设计、零件和装配步骤。', example: '复现这套硬件需要哪些材料和步骤？', icon: ListChecks },
];
const validId = (id) => /^[a-z0-9-]{1,80}$/.test(id || '');
const noteLimit = 600;

async function prepareImage(file) {
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > 16 * 1024 * 1024) {
    throw new Error('请选择 16 MB 以内的 JPEG、PNG 或 WebP。');
  }
  const bitmap = await createImageBitmap(file);
  const canvas = document.createElement('canvas');
  try {
    const scale = Math.min(1, 1280 / Math.max(bitmap.width, bitmap.height));
    canvas.width = Math.max(1, Math.round(bitmap.width * scale));
    canvas.height = Math.max(1, Math.round(bitmap.height * scale));
    const context = canvas.getContext('2d');
    if (!context) throw new Error('无法处理图片。');
    context.fillStyle = '#fff';
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    const data = canvas.toDataURL('image/jpeg', 0.78);
    if (data.length > 2 * 1024 * 1024) throw new Error('压缩后的图片仍然过大。');
    return data;
  } finally {
    bitmap.close();
  }
}

function dateLabel(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { dateStyle: 'short', timeStyle: 'short' });
}

function RunResult({ run, save, saving }) {
  if (!run) return <Empty>运行一个工作流，这里会显示研究步骤、结论和引用。</Empty>;
  const steps = run.steps || [];
  return (
    <section className="surface run-result" aria-live="polite">
      <div className="panel-heading"><h2>研究结果</h2><span className="badge accent">{run.mode === 'model' ? '模型与目录' : '目录证据模式'}</span></div>
      {run.warning ? <p className="research-warning">{run.warning}</p> : null}
      {steps.length ? <ol className="workflow-steps">{steps.map((step, index) => <li key={`${step.name}-${index}`}><span>{String(index + 1).padStart(2, '0')}</span><strong>{step.name}</strong><p>{step.detail}</p></li>)}</ol> : null}
      <div className="answer-text">{run.answer}</div>
      {run.citations?.length ? <div className="citation-list"><h3>引用来源</h3><ul>{run.citations.map((citation, index) => <li key={`${citation.id}-${index}`}><span className="badge">{citation.id}</span><div><External className="inline-link" href={citation.url}>{citation.title}</External>{citation.locator ? <small>{citation.locator}</small> : null}{citation.productId ? <Link to={`/products/${encodeURIComponent(citation.productId)}`}>查看档案 <ArrowRight size={14} /></Link> : null}</div></li>)}</ul></div> : null}
      <button className="button small" onClick={() => save(run.answer.slice(0, noteLimit))} disabled={saving || !run.answer?.trim()}><BookmarkSimple size={17} /> {run.answer?.length > noteLimit ? '保存前 600 字为笔记' : '保存为研究笔记'}</button>
    </section>
  );
}

function ResearchWorkspace({ initialProducts, initialPart, initialWorkflow }) {
  const catalog = useResource('/catalog?limit=100');
  const config = useResource('/research/config');
  const history = useResource('/research/history', { workspace: true });
  const memory = useResource('/research/notes', { workspace: true });
  const [workflow, setWorkflow] = useState(initialWorkflow);
  const [query, setQuery] = useState('');
  const [productIds, setProductIds] = useState(initialProducts);
  const [useMemory, setUseMemory] = useState(false);
  const [image, setImage] = useState(null);
  const [imageBusy, setImageBusy] = useState(false);
  const [allowImageTransfer, setAllowImageTransfer] = useState(false);
  const [imageError, setImageError] = useState('');
  const [run, setRun] = useState(null);
  const [busy, setBusy] = useState(false);
  const [runError, setRunError] = useState('');
  const [note, setNote] = useState('');
  const [noteBusy, setNoteBusy] = useState(false);
  const [noteStatus, setNoteStatus] = useState('');
  const [noteError, setNoteError] = useState('');
  const [clearHistory, setClearHistory] = useState(false);
  const [historyError, setHistoryError] = useState('');
  const partId = productIds.includes(initialProducts[0]) ? initialPart : undefined;
  const current = workflows.find((item) => item.id === workflow);
  const products = catalog.value?.products || [];
  const currentPart = products.find((product) => product.id === initialProducts[0])?.parts.find((item) => item.id === partId);

  function toggle(id) {
    setProductIds((ids) => ids.includes(id) ? ids.filter((item) => item !== id) : ids.length < 4 ? [...ids, id] : ids);
  }

  async function chooseImage(event) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    setImageBusy(true);
    setImageError('');
    setImage(null);
    setAllowImageTransfer(false);
    try {
      setImage({ name: file.name, data: await prepareImage(file) });
    } catch (error) {
      setImageError(error.message || '无法读取图片。');
    } finally {
      setImageBusy(false);
    }
  }

  async function runWorkflow(event) {
    event.preventDefault();
    if (busy || (!query.trim() && !image) || (image && !allowImageTransfer)) return;
    setBusy(true);
    setRunError('');
    try {
      setRun(await request('/research/run', {
        method: 'POST', workspace: true,
        body: { workflow, query: query.trim(), productIds, partId, useMemory, image: image?.data, allowImageTransfer: image ? allowImageTransfer : undefined },
      }));
      history.retry();
    } catch (error) {
      setRunError(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function saveNote(value) {
    if (!value.trim() || noteBusy) return;
    setNoteBusy(true);
    setNoteStatus('');
    setNoteError('');
    try {
      await request('/research/notes', { method: 'POST', workspace: true, body: { text: value.trim() } });
      if (value === note) setNote('');
      setNoteStatus('已保存到研究笔记。');
      memory.retry();
    } catch (error) {
      setNoteError(error.message);
    } finally {
      setNoteBusy(false);
    }
  }

  async function deleteNote(id) {
    setNoteBusy(true);
    setNoteError('');
    setNoteStatus('');
    try {
      await request(`/research/notes/${encodeURIComponent(id)}`, { method: 'DELETE', workspace: true });
      memory.retry();
    } catch (error) {
      setNoteError(error.message);
    } finally {
      setNoteBusy(false);
    }
  }

  async function deleteHistory() {
    setClearHistory(false);
    setHistoryError('');
    try {
      await request('/research/history', { method: 'DELETE', workspace: true });
      setRun(null);
      history.retry();
    } catch (error) {
      setHistoryError(error.message);
    }
  }

  return (
    <div className="research-layout">
      <div className="research-main">
        <form className="surface form-stack" onSubmit={runWorkflow}>
          <h2><Flask size={23} /> 新建研究</h2>
          <div className="workflow-grid" aria-label="选择工作流">
            {workflows.map(({ id, label, description, icon: Icon }) => <button key={id} type="button" className={workflow === id ? 'active' : ''} aria-pressed={workflow === id} onClick={() => setWorkflow(id)}><Icon size={23} /><strong>{label}</strong><small>{description}</small></button>)}
          </div>
          <fieldset className="context-picker">
            <legend>研究对象 <span className="mono">{productIds.length}/4</span></legend>
            <div className="parts-index">{productIds.map((id) => <button type="button" key={id} className="active" onClick={() => toggle(id)}>{products.find((product) => product.id === id)?.name || id}<X size={14} /></button>)}</div>
            {partId ? <span className="badge accent">选中部件 · {currentPart?.name || partId}</span> : null}
            <label><span className="sr-only">添加研究对象</span><select value="" onChange={(event) => { if (event.target.value) toggle(event.target.value); }} disabled={productIds.length >= 4 || catalog.loading}><option value="">添加档案（选填）</option>{products.filter((product) => !productIds.includes(product.id)).map((product) => <option key={product.id} value={product.id}>{product.name}</option>)}</select></label>
            <Status resource={catalog} />
          </fieldset>
          <label>研究问题<textarea rows={4} maxLength={1200} value={query} onChange={(event) => setQuery(event.target.value)} placeholder={current.example} /></label>
          <button type="button" className="text-button example-button" onClick={() => setQuery(current.example)}>使用示例问题 <ArrowRight size={15} /></button>
          <label className="check-filter"><input type="checkbox" checked={useMemory} onChange={(event) => setUseMemory(event.target.checked)} /> 本次使用已保存的研究笔记</label>
          {config.value?.visionEnabled ? (
            <div className="image-picker">
              <label><span><ImageSquare size={17} /> 添加部件照片（选填）</span><input type="file" accept="image/jpeg,image/png,image/webp" onChange={chooseImage} disabled={imageBusy} /></label>
              {imageBusy ? <p role="status">正在处理照片…</p> : null}
              {imageError ? <p role="alert" className="error-text">{imageError}</p> : null}
              {image ? <><div className="image-preview"><img src={image.data} alt="待提交的部件照片" /><span>{image.name}</span><button type="button" className="icon-button" aria-label="移除照片" onClick={() => { setImage(null); setAllowImageTransfer(false); }}><X size={17} /></button></div><label className="check-filter"><input type="checkbox" checked={allowImageTransfer} onChange={(event) => setAllowImageTransfer(event.target.checked)} /> 允许将此照片发送至配置的视觉模型</label></> : null}
            </div>
          ) : null}
          {runError ? <p role="alert" className="error-text">{runError}</p> : null}
          <button className="button primary" disabled={busy || imageBusy || (!query.trim() && !image) || Boolean(image && !allowImageTransfer)} type="submit">{busy ? <SpinnerGap className="spinner" size={18} /> : <ArrowRight size={18} />}{busy ? '正在研究…' : '运行工作流'}</button>
        </form>
        <RunResult run={run} save={saveNote} saving={noteBusy} />
      </div>
      <aside className="research-side">
        <section className="surface">
          <h2><BookmarkSimple size={21} /> 研究笔记</h2>
          <p className="muted">可随时查看或删除。运行工作流时可选择使用这些笔记。</p>
          <form className="form-stack" onSubmit={(event) => { event.preventDefault(); saveNote(note); }}>
            <label><span className="sr-only">添加笔记</span><textarea value={note} maxLength={noteLimit} rows={3} onChange={(event) => setNote(event.target.value)} placeholder="记下一个发现或研究偏好…" /></label>
            <button className="button small" disabled={!note.trim() || noteBusy}><BookmarkSimple size={16} /> 保存笔记</button>
          </form>
          {noteStatus ? <p className="success-text" role="status"><CheckCircle size={16} /> {noteStatus}</p> : null}
          {noteError ? <p role="alert" className="error-text">{noteError}</p> : null}
          <Status resource={memory} />
          {memory.value?.notes?.length ? <ul className="notes-list">{memory.value.notes.map((item) => <li key={item.id}><p>{item.text}</p><small>{dateLabel(item.createdAt)}</small><button className="icon-button" aria-label="删除笔记" disabled={noteBusy} onClick={() => deleteNote(item.id)}><Trash size={17} /></button></li>)}</ul> : null}
        </section>
        <section className="surface">
          <h2><ClockCounterClockwise size={21} /> 研究记录</h2>
          <Status resource={history} />
          {historyError ? <p role="alert" className="error-text">{historyError}</p> : null}
          {history.value && !history.value.runs?.length ? <p className="muted">暂无记录。</p> : null}
          {history.value?.runs?.length ? <><ul className="history-list">{history.value.runs.map((item) => <li key={item.id}><button aria-pressed={run?.id === item.id} onClick={() => setRun(item)}><span>{item.query || item.answer.slice(0, 32) || '研究结果'}</span><small>{dateLabel(item.createdAt)}</small></button></li>)}</ul>{clearHistory ? <div className="action-row"><button className="button small primary" onClick={deleteHistory}>确认清空</button><button className="button small" onClick={() => setClearHistory(false)}>取消</button></div> : <button className="text-button" onClick={() => setClearHistory(true)}><Trash size={15} /> 清空记录</button>}</> : null}
        </section>
      </aside>
    </div>
  );
}

export function Research() {
  const [params] = useSearchParams();
  const productIds = [...new Set(params.getAll('product').filter(validId))].slice(0, 4);
  const part = validId(params.get('part')) ? params.get('part') : undefined;
  const initialWorkflow = workflows.some((item) => item.id === params.get('workflow')) ? params.get('workflow') : 'search';
  return (
    <div className="wrap page-top research-page">
      <Link className="inline-link breadcrumb" to="/"><ArrowLeft size={16} /> 硬件档案</Link>
      <div className="page-intro"><span className="eyebrow"><span className="signal-dot" /> LAB / 03</span><h1>硬件研究室。</h1><p>带上一个问题，沿着型号、部件和证据继续研究。</p></div>
      <ResearchWorkspace key={params.toString()} initialProducts={productIds} initialPart={part} initialWorkflow={initialWorkflow} />
    </div>
  );
}
