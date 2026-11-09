import { Cube, Eyeglasses, GridFour, Monitor, Robot, SpeakerHigh, SquaresFour } from '@phosphor-icons/react';

export const categories = [
  { id: 'toy', label: 'AI 玩具', english: 'COMPANIONS', icon: Robot },
  { id: 'glasses', label: 'AI 眼镜', english: 'WEARABLES', icon: Eyeglasses },
  { id: 'speaker', label: 'AI 音箱', english: 'VOICE', icon: SpeakerHigh },
  { id: 'mirror', label: 'AI 镜子', english: 'MIRRORS', icon: GridFour },
  { id: 'cabinet', label: 'AI 柜子', english: 'CABINETS', icon: SquaresFour },
  { id: 'desk', label: 'AI 电脑桌', english: 'DESKS', icon: Monitor },
];

export function categoryFor(id) {
  return categories.find((item) => item.id === id) || { label: id, english: 'HARDWARE', icon: Cube };
}

export const kindLabels = { commercial: '商业产品', open: '开源项目', reference: '参考方案', module: '硬件模块' };
export const computeLabels = { device: '设备端', phone: '手机端', lan: '局域网', cloud: '厂商云', mixed: '端云协同', unknown: '待核验' };
export const sourceLabels = { official: '官方', teardown: '实物拆解', open: '开源', manual: '手册', other: '参考' };
export const partLabels = { confirmed: '已确认', observed: '拆解观察', inferred: '推断', unknown: '待核验' };
export const modelLabels = { reconstruction: '依据拆解重建', concept: '概念示意', official: '原厂模型', scan: '实物扫描' };
export const imageLabels = {
  concept: '概念示意',
  reconstruction: '重建示意',
  official: '官方产品照片',
  retail: '销售页面图片',
  photo: '实物实拍',
  teardown: '实物拆解照片',
};

export function productPhotos(product) {
  const candidates = [product?.image, ...(product?.photos || [])];
  const photos = new Map();
  for (const candidate of candidates) {
    if (!candidate?.url || !['official', 'retail', 'photo', 'teardown'].includes(candidate.type)) continue;
    const previous = photos.get(candidate.url);
    if (!previous || (!previous.sourceId && candidate.sourceId)) photos.set(candidate.url, candidate);
  }
  return [...photos.values()];
}

export function photoSource(product, photo) {
  return product?.sources?.find(({ id }) => id === photo?.sourceId);
}

export function safeLink(value) {
  try {
    const url = new URL(value);
    return ['https:', 'http:'].includes(url.protocol) ? url.href : undefined;
  } catch {
    return undefined;
  }
}

export function researchUrl(productId, partId, workflow = 'evidence') {
  const query = new URLSearchParams({ workflow });
  if (productId) query.set('product', productId);
  if (partId) query.set('part', partId);
  return `/research?${query}`;
}
