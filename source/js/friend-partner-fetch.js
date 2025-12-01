'use strict';

/**
 * 用途：前端根据 link_list 里的 UID 调用 API 获取“小伙伴”资料，并动态渲染友链卡片。
 * 额外：对“框架”“推荐博客”“小伙伴”分组的友链进行随机排序，并修复顶部头像/卡片 404。
 * 流程：检测友链页 -> 解析 UID 列表 -> 请求 API -> 渲染卡片 -> 同步顶部头像 -> 随机排序 -> 刷新懒加载。
 */
(() => {
  const PARTNER_CLASS_NAME = '小伙伴';
  const API_BASE = 'https://api.yumeharu.top/api/getuser?type=json&mid=';
  const AVATAR_REDIRECT = mid => `https://api.yumeharu.top/api/getuser?mid=${mid}&type=avatar_redirect`;
  const MANIFEST_URL = '/partner-uids.json';
  const ERROR_AVATAR = '/img/friend_404.gif';
  const RENDERED_FLAG = 'partnerRendered';
  const RETRY_DELAY = 500; // 首屏兜底重试间隔（毫秒）
  const MAX_UID_ATTEMPTS = 3; // 获取 UID 的最大尝试次数
  const MAX_PROFILE_ATTEMPTS = 3; // 拉取资料的最大尝试次数
  const SHUFFLE_TARGETS = ['框架', '推荐博客', '小伙伴']; // 需要随机排序的分组

  let manifestUids = null;
  let cachedFriends = null;
  let baselineFriends = [];
  let baselineMids = [];

  // 判断当前是否为友链页面（兼容 pjax 和直接访问）
  const isLinkPage = () => {
    const pageType = document.getElementById('page-type')?.value;
    if (pageType) return pageType === 'link';
    const path = location.pathname.replace(/\/+$/, '');
    return path === '/link' || path === '/link/index.html';
  };

  // 将获取到的朋友数据渲染到页面并刷新懒加载
  const render = (section, friends) => {
    if (!section || !section.list) return;
    const useLazy = Boolean(window.GLOBAL_CONFIG && window.GLOBAL_CONFIG.islazyload);
    section.list.innerHTML = '';
    friends.forEach(friend => {
      section.list.appendChild(createCard(friend, useLazy));
    });
    if (section.heading) {
      section.heading.textContent = `${PARTNER_CLASS_NAME}(${friends.length})`;
    }
    section.list.dataset[RENDERED_FLAG] = '1';
    if (useLazy && window.lazyLoadInstance && typeof window.lazyLoadInstance.update === 'function') {
      window.lazyLoadInstance.update();
    }
  };

  // 从对象或原始值中提取 mid；支持 {mid,uid} 或数字/字符串
  const extractMid = entry => {
    if (entry && typeof entry === 'object') return entry.mid || entry.uid || '';
    return entry;
  };

  // 判断是否为纯数字 UID
  const isUid = value =>
    typeof value === 'number' || (typeof value === 'string' && /^\d+$/.test(value));

  // 数组去重工具
  const unique = list => Array.from(new Set(list.map(String)));

  // 规范化基线友链数据（用于失败时兜底渲染）
  const normalizeBaseline = entry => {
    if (entry && typeof entry === 'object') {
      const mid = entry.mid || entry.uid || '';
      return {
        mid: mid ? String(mid) : '',
        name: entry.name || (mid ? String(mid) : '伙伴'),
        link: entry.link || (mid ? `https://space.bilibili.com/${mid}` : '#'),
        avatar: entry.avatar || (mid ? AVATAR_REDIRECT(mid) : ERROR_AVATAR),
        descr: entry.descr || ''
      };
    }
    const mid = entry ? String(entry) : '';
    return {
      mid,
      name: mid || '伙伴',
      link: mid ? `https://space.bilibili.com/${mid}` : '#',
      avatar: mid ? AVATAR_REDIRECT(mid) : ERROR_AVATAR,
      descr: ''
    };
  };

  // 捕获全局 friend_link_list 作为兜底数据
  const captureBaseline = () => {
    if (!Array.isArray(window.friend_link_list)) return;
    baselineFriends = window.friend_link_list.map(normalizeBaseline);
    baselineMids = baselineFriends.map(f => f.mid).filter(Boolean);
  };

  // 定位“小伙伴”分组的标题和列表容器
  const findPartnerSection = () => {
    const heading = Array.from(document.querySelectorAll('.flink h2')).find(node => {
      const text = (node.textContent || '').replace(/\([^)]*\)/g, '').trim();
      return text === PARTNER_CLASS_NAME;
    });

    if (!heading) return null;

    let list = heading.nextElementSibling;
    while (list && !list.classList?.contains('anzhiyu-flink-list')) {
      list = list.nextElementSibling;
    }

    if (!list) return null;
    return { heading, list };
  };

  // 从主题生成的全局 friend_link_list 获取 UID（已在后端 normalize 过）
  const uidListFromGlobal = () => {
    if (!Array.isArray(window.friend_link_list)) return [];
    return unique(window.friend_link_list.map(extractMid).filter(isUid));
  };

  // 优先：从生成好的 manifest（partner-uids.json）读取 UID，避免竞态
  const uidListFromManifest = async () => {
    if (manifestUids) return manifestUids;
    const res = await fetch(MANIFEST_URL, { cache: 'no-store' });
    if (!res.ok) throw new Error(`Manifest HTTP ${res.status}`);
    const payload = await res.json();
    const uids = Array.isArray(payload.uids) ? payload.uids : [];
    const manifestList = unique(uids.filter(isUid));
    // 与页面的基线数据合并，避免旧缓存丢掉新添加的 UID
    manifestUids = baselineMids.length ? unique([...manifestList, ...baselineMids.filter(isUid)]) : manifestList;
    if (!manifestUids.length) throw new Error('Manifest empty');
    return manifestUids;
  };

  // 兜底：从 /anzhiyu/random.js 中解析 UID 列表（与原主题逻辑一致）
  const uidListFromRandomScript = async () => {
    try {
      const res = await fetch('/anzhiyu/random.js', { cache: 'no-store' });
      if (!res.ok) return [];
      const scriptText = await res.text();
      const match = scriptText.match(/friend_link_list=([^;]+);/);
      if (!match || !match[1]) return [];
      const parsed = JSON.parse(match[1]);
      return unique(parsed.map(extractMid).filter(isUid));
    } catch (error) {
      console.error('[friend-partner] Unable to read UID list from random.js', error);
      return [];
    }
  };

  // 按优先级获取 UID 列表
  const getUidList = async () => {
    // 1. manifest（构建时写入），最稳定
    try {
      return await uidListFromManifest();
    } catch (err) {
      console.warn('[friend-partner] manifest unavailable, fallback to globals', err);
    }

    // 2. 全局 friend_link_list（random.js 运行后提供）
    const fromGlobal = uidListFromGlobal();
    if (fromGlobal.length) return fromGlobal;

    // 3. 直接读取 random.js 文件作为兜底
    const fromScript = await uidListFromRandomScript();
    if (fromScript.length) return fromScript;

    // 4. 基线兜底（保证至少用 UID 占位，不再为空）
    if (baselineMids.length) return unique(baselineMids.filter(isUid));
    return [];
  };

  // 请求 API，返回带 name/link/avatar/descr 的朋友信息
  const fetchProfiles = async mids => {
    if (!mids.length) return [];
    const url = API_BASE + encodeURIComponent(mids.join(','));
    const response = await fetch(url);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    if (!payload || payload.code !== 0 || !payload.data) {
      throw new Error('Unexpected API payload');
    }
    return mids.map(mid => {
      const info = payload.data[mid] || {};
      return {
        mid,
        name: info.name || mid,
        link: `https://space.bilibili.com/${mid}`,
        avatar: info.face || AVATAR_REDIRECT(mid) || ERROR_AVATAR,
        descr: info.sign || ''
      };
    });
  };

  // 通用重试方法，避免首屏竞态导致未获取到 UID / API 数据
  const retry = async (task, attempts, delay) => {
    let lastErr = null;
    for (let i = 0; i < attempts; i += 1) {
      try {
        const result = await task();
        return result;
      } catch (err) {
        lastErr = err;
        if (i < attempts - 1) {
          await new Promise(resolve => setTimeout(resolve, delay));
        }
      }
    }
    throw lastErr;
  };

  // 生成单个友链卡片 DOM，兼容懒加载
  const createCard = (friend, useLazy) => {
    const item = document.createElement('div');
    item.className = 'flink-list-item';

    const anchor = document.createElement('a');
    anchor.className = 'cf-friends-link';
    anchor.href = friend.link;
    anchor.setAttribute('cf-href', friend.link);
    anchor.title = friend.name;
    anchor.target = '_blank';

    const img = document.createElement('img');
    img.className = 'cf-friends-avatar no-lightbox';
    img.alt = friend.name;
    img.setAttribute('cf-src', friend.avatar);
    img.onerror = function handleError() {
      this.onerror = null;
      this.src = ERROR_AVATAR;
    };

    if (useLazy) {
      img.setAttribute('data-lazy-src', friend.avatar);
    } else {
      img.src = friend.avatar;
    }

    const info = document.createElement('div');
    info.className = 'flink-item-info';

    const name = document.createElement('div');
    name.className = 'flink-item-name cf-friends-name';
    name.textContent = friend.name;

    const desc = document.createElement('div');
    desc.className = 'flink-item-desc';
    desc.title = friend.descr || friend.name;
    desc.textContent = friend.descr || '';

    info.appendChild(name);
    info.appendChild(desc);
    anchor.appendChild(img);
    anchor.appendChild(info);
    item.appendChild(anchor);

    return item;
  };

  // 将获取到的伙伴头像同步到顶部「skills-tags-group-all」区域，避免出现 404
  const updateSkillsAvatars = friends => {
    if (!friends || !friends.length) return;
    const pairs = Array.from(document.querySelectorAll('#skills-tags-group-all .tags-group-icon-pair a'));
    pairs.forEach(anchor => {
      const img = anchor.querySelector('img');
      if (!img) return;
      const href = anchor.getAttribute('href') || anchor.getAttribute('cf-href') || '';
      const match = friends.find(f => href.includes(`/space.bilibili.com/${f.mid}`) || href.endsWith(`${f.mid}`));
      if (!match) return;
      img.src = match.avatar || ERROR_AVATAR;
      img.setAttribute('cf-src', match.avatar || ERROR_AVATAR);
      img.removeAttribute('data-lazy-src');
      img.onerror = function handleError() {
        this.onerror = null;
        this.src = ERROR_AVATAR;
      };
    });
  };

  // 随机打乱一个容器下的子元素顺序
  const shuffleContainer = container => {
    if (!container) return;
    const items = Array.from(container.children);
    if (!items.length) return;
    for (let i = items.length - 1; i > 0; i -= 1) {
      const j = Math.floor(Math.random() * (i + 1));
      [items[i], items[j]] = [items[j], items[i]];
    }
    container.innerHTML = '';
    items.forEach(el => container.appendChild(el));
  };

  // 控制整体显示/隐藏，避免用户看到排序过程（配合 head 中的 CSS）
  const markShuffleReady = ready => {
    const cls = 'partner-shuffle-ready';
    if (ready) document.body.classList.add(cls);
    else document.body.classList.remove(cls);
  };

  // 查找 h2 后对应的友链容器（兼容 anzhiyu / telescopic / flexcard）
  const findContainerAfterHeading = heading => {
    if (!heading) return null;
    let node = heading.nextElementSibling;
    while (node) {
      if (
        node.classList?.contains('anzhiyu-flink-list') ||
        node.classList?.contains('telescopic-site-card-group') ||
        node.classList?.contains('flexcard-flink-list')
      ) {
        return node;
      }
      node = node.nextElementSibling;
    }
    return null;
  };

  // 收集需要随机排序的容器，并在排序前隐藏，避免用户看到排序过程
  const collectShuffleContainers = () => {
    const containers = [];
    const headings = Array.from(document.querySelectorAll('.flink h2'));
    headings.forEach(h2 => {
      const text = (h2.textContent || '').replace(/\([^)]*\)/g, '').trim();
      if (!SHUFFLE_TARGETS.includes(text)) return;
      const container = findContainerAfterHeading(h2);
      if (container) containers.push(container);
    });
    return containers;
  };

  // 随机排序指定分组
  const shuffleTargetSections = () => {
    const useLazy = Boolean(window.GLOBAL_CONFIG && window.GLOBAL_CONFIG.islazyload);
    const containers = collectShuffleContainers();
    if (!containers.length) return;

    containers.forEach(container => {
      shuffleContainer(container);
    });

    if (useLazy && window.lazyLoadInstance && typeof window.lazyLoadInstance.update === 'function') {
      window.lazyLoadInstance.update();
    }
  };

  // 执行主流程，使用缓存避免重复请求
  const run = async (uidAttemptsLeft = MAX_UID_ATTEMPTS, profileAttemptsLeft = MAX_PROFILE_ATTEMPTS) => {
    if (!isLinkPage()) return;
    const section = findPartnerSection();
    if (!section || !section.list || section.list.dataset[RENDERED_FLAG] === '1') return;

    try {
      if (!cachedFriends) {
        // 获取 UID，加入重试避免首屏竞态
        const mids = await retry(() => getUidList(), uidAttemptsLeft, RETRY_DELAY);
        if (!mids.length) throw new Error('No UID found');
        // 获取资料，加入重试避免临时网络波动
        cachedFriends = await retry(() => fetchProfiles(mids), profileAttemptsLeft, RETRY_DELAY);
      }
      render(section, cachedFriends);
      updateSkillsAvatars(cachedFriends);
      shuffleTargetSections();
      markShuffleReady(true);
    } catch (error) {
      // 如果还有重试机会，稍后再试；否则用基线数据兜底，保证页面不空
      if (uidAttemptsLeft > 1 || profileAttemptsLeft > 1) {
        setTimeout(() => run(uidAttemptsLeft - 1, profileAttemptsLeft - 1), RETRY_DELAY);
      } else {
        const fallback = baselineFriends.length ? baselineFriends : [];
        if (fallback.length && section && section.list) {
          render(section, fallback);
          updateSkillsAvatars(fallback);
          shuffleTargetSections();
          markShuffleReady(true);
        }
        console.error('[friend-partner] Failed to render partners after retry', error);
      }
    }
  };

  // 安全执行（捕获异常），兼容首屏和 pjax 刷新
  const safeRun = async () => {
    if (!isLinkPage()) return;
    // 先捕获基线数据，保证兜底可用
    captureBaseline();
    markShuffleReady(false);
    try {
      await run();
    } catch (error) {
      console.error('[friend-partner] Failed to render partners', error);
    } finally {
      // 所有目标分组做一次随机排序（无论“小伙伴”是否需要动态渲染）
      if (cachedFriends && cachedFriends.length) updateSkillsAvatars(cachedFriends);
      shuffleTargetSections();
      markShuffleReady(true);
    }
  };

  document.addEventListener('DOMContentLoaded', safeRun, false);
  document.addEventListener('pjax:complete', safeRun, false);
})();
