/*
 * 用途：修复 About 页“音乐偏好-更多推荐”按钮在 PJAX 场景下的跨域报错问题，
 */
(() => {
  const FLAG_ATTR = 'musicLinkFixed';

  const applyFix = () => {
    // 定位“更多推荐”按钮；若不存在则直接返回（例如不在 About 页）
    const musicButton = document.querySelector('#about-page .like-music .banner-button');
    if (!musicButton) return;
    // 若已处理过则不重复绑定
    if (musicButton.dataset[FLAG_ATTR] === 'true') return;

    // 解析主题原先写在 onclick 里的 QQ 音乐歌单链接
    const legacyOnclick = musicButton.getAttribute('onclick') || '';
    const legacyLinkMatch = legacyOnclick.match(/"(.*?)"/);
    const legacyLink = legacyLinkMatch ? legacyLinkMatch[1] : '';

    // 移除主题原有的 PJAX onclick，避免再次触发跨域的 PJAX 请求
    musicButton.removeAttribute('onclick');

    // 补全普通超链接，便于无脚本/键盘访问场景仍可跳转
    if (!musicButton.hasAttribute('href') && legacyLink) {
      musicButton.setAttribute('href', legacyLink);
      musicButton.setAttribute('rel', 'noopener');
    }

    musicButton.addEventListener('click', event => {
      event.preventDefault(); // 阻止主题或浏览器默认行为，彻底绕开 PJAX
      const linkFromDataset = musicButton.dataset.link; // 支持模板自定义 data-link
      const link = linkFromDataset || legacyLink || musicButton.href; // 优先级：data-link > 解析出的 onclick > href
      if (!link) return; // 未取得有效链接则不做处理
      window.open(link, '_blank', 'noopener'); // 新标签页直开 QQ 歌单
    });

    // 标记已处理，避免重复绑定
    musicButton.dataset[FLAG_ATTR] = 'true';
  };

  const init = () => applyFix();

  // 首次完整加载
  document.addEventListener('DOMContentLoaded', init);
  // PJAX 部分刷新后重新绑定
  document.addEventListener('pjax:complete', init);

  // 若脚本在 DOMContentLoaded 之后才插入，也立即执行一次
  if (document.readyState === 'interactive' || document.readyState === 'complete') {
    init();
  }
})();
