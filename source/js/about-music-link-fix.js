/**
 * about-music-link-fix.js
 * 目的：修复关于页面“音乐偏好 → 更多推荐”按钮在 PJAX 场景下触发的跨域错误。
 * 原因：主题模板为按钮绑定了 pjax.loadUrl(...)，浏览器会以 XHR 方式访问 QQ 音乐，但该站点未设置 CORS 允许头，导致请求被拒绝。
 * 作用：拦截按钮点击，改用普通超链接方式打开歌单页面，避免触发跨域验证。
 */
document.addEventListener('DOMContentLoaded', () => {
  // 锁定关于页面里音乐推荐区域的按钮。如果当前页面没有该元素，直接停止后续逻辑。
  const musicButton = document.querySelector('#about-page .like-music .banner-button');
  if (!musicButton) return;

  // 移除主题模板设置的 onclick="pjax.loadUrl(...)"，防止跨域请求再次被触发。
  musicButton.removeAttribute('onclick');

  musicButton.addEventListener('click', event => {
    // 阻止默认行为，避免主题脚本或浏览器继续执行原本的 PJAX 路径。
    event.preventDefault();

    /**
     * 为兼容不同配置，按优先级读取按钮的目标链接：
     * 1. data-link（若在模板中手动设置自定义 data 属性）
     * 2. 历史版本 onclick 留下的链接（兼容未清理干净的旧写法）
     * 3. a 标签自身的 href
     */
    const linkFromDataset = musicButton.dataset.link;
    const linkFromLegacyOnclick = musicButton.getAttribute('onclick')?.match(/"(.*?)"/)?.[1];
    const link = linkFromDataset || linkFromLegacyOnclick || musicButton.href;

    if (!link) return;

    // 使用新标签页打开 QQ 音乐歌单，既绕过 CORS，也保留当前页面的浏览状态。
    window.open(link, '_blank', 'noopener');
  });
});
