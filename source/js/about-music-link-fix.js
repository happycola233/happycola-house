/**
 * about-music-link-fix.js
 * 目的：修复关于页面“音乐偏好 · 更多推荐”按钮在 PJAX 场景下触发的跨域错误，保证用户能正常打开 QQ 音乐歌单。
 * 背景：主题模板为按钮绑定了 `pjax.loadUrl(...)`，在 PJAX 场景下会以 XHR 请求 QQ 音乐，因对方未设置 CORS 允许头导致请求被拒。
 * 方案：在移除 onclick 前预先解析出原始链接，将跳转转换为普通新标签页打开，同时补充 href 保证无脚本场景的可访问性。
 */
document.addEventListener('DOMContentLoaded', () => {
  // 查找关于页面音乐推荐区域的按钮；若当前页不存在该按钮，直接结束脚本。
  const musicButton = document.querySelector('#about-page .like-music .banner-button');
  if (!musicButton) return;

  /**
   * 在移除 onclick 之前先缓存原始属性值，并利用正则匹配其中的 URL。
   * 这样即便后续删除掉 onclick 也能保留旧链接，避免再次访问 DOM 取不到地址。
   */
  const legacyOnclick = musicButton.getAttribute('onclick') || '';
  const legacyLinkMatch = legacyOnclick.match(/"(.*?)"/);
  const legacyLink = legacyLinkMatch ? legacyLinkMatch[1] : '';

  // 移除主题原先的 onclick="pjax.loadUrl(...)"，防止继续触发跨域的 PJAX 请求。
  musicButton.removeAttribute('onclick');

  /**
   * 若按钮缺少 href（主题默认如此），且成功解析出旧链接，则补上 href + rel="noopener"。
   * 这样无脚本或键盘访问也能退回普通跳转，提升可访问性。
   */
  if (!musicButton.hasAttribute('href') && legacyLink) {
    musicButton.setAttribute('href', legacyLink);
    musicButton.setAttribute('rel', 'noopener');
  }

  musicButton.addEventListener('click', event => {
    // 阻止浏览器或主题后续默认行为，彻底避免回落到 PJAX 流程。
    event.preventDefault();

    /**
     * 按优先级读取按钮最终要打开的链接：
     * 1. 自定义 data-link（若用户在模板中额外设置）
     * 2. 缓存的旧 onclick 链接（主题原始写法）
     * 3. 当前 a 标签的 href（可能是上一步补充的值）
     */
    const linkFromDataset = musicButton.dataset.link;
    const link = linkFromDataset || legacyLink || musicButton.href;

    if (!link) return;

    // 使用新标签页打开 QQ 音乐歌单，既避开 CORS 限制，也保留当前页面的浏览状态。
    window.open(link, '_blank', 'noopener');
  });
});
