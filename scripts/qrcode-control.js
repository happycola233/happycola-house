/**
 * 【作用】按主题配置与页面实际是否包含容器，决定是否向浏览器发送 qrcode.min.js。
 * 【据调查】
 * - node_modules\hexo-theme-anzhiyu\layout\includes\additional-js.pug:101 无视 _config.anzhiyu.yml:254 的 reward.enable，
 *   总是注入 qrcode.min.js，因此即使“打赏/扫码”功能关闭也会加载该脚本，此脚本的请求严重拖慢了网站的加载速度。
 * - 该脚本当前仅用于文章底部的“手机扫码阅读”（theme.ptool.share_mobile）区块，该区块由
 *   node_modules\hexo-theme-anzhiyu\layout\includes\post\ptool.pug:24 渲染；同时
 *   node_modules\hexo-theme-anzhiyu\source\js\main.js:1829 的 anzhiyu.qrcodeCreate() 无条件执行。
 *
 * 【实现思路】
 *  1）先统一“剥离”主题默认注入的 <script ... qrcode.min.js>，保证每个页面从干净状态开始；
 *  2）仅当配置确实需要（reward 或 ptool.share_mobile 为真）且页面包含 #qrcode 容器时，才在 </body> 前追加脚本（PJAX 友好）；
 *  3）对 anzhiyu.qrcodeCreate() 做防守式封装：若全局 QRCode 不存在则静默跳过，避免报错。
 *
 * 【带来的好处】
 * - 关闭“打赏/扫码”或页面没有扫码容器时，不再下载 qrcode.min.js，减少无效请求与体积；
 * - 首页/归档等不含扫码模块的页面保持干净；
 * - PJAX 场景下脚本只在需要时、以正确的时机注入，避免重复或顺序问题。
 */
'use strict';

/** 
 * QR 源地址（CDN）。如主题未来更换版本或域名，只需修改此处常量。
 * 说明：使用外链而非主题内置路径，是为了可控与解耦；也便于统一匹配与移除。
 */
const QR_SRC = 'https://cdn.cbd.int/qrcodejs@1.0.0/qrcode.min.js';

/**
 * 需要注入的 <script> 片段。
 * data-pjax 属性：配合主题的 PJAX 机制，确保切页后脚本可被重新识别/执行（由主题约定）。
 */
const QR_TAG = `<script data-pjax src="${QR_SRC}"></script>`;

/**
 * 用于“剥离”主题已注入脚本的正则：
 * - 动态转义 QR_SRC 中的正则特殊字符，确保精确匹配目标 src；
 * - <script ... src="..."></script> 允许包含任意其他属性；
 * - 结尾的 \\s* 便于吃掉尾部空白，避免留下多余空行；
 * - 标志位 i（忽略大小写）、g（全局替换）。
 *
 * 小心点：因为使用了全局 g，每次替换前务必重置 lastIndex=0，避免跨页面缓存导致遗漏。
 */
const QR_REGEX = new RegExp(
  `<script[^>]*src=["']${QR_SRC.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&')}["'][^>]*></script>\\s*`,
  'ig'
);

hexo.extend.filter.register('after_render:html', (html) => {
  /**
   * 【阶段一：统一清场】
   * 无论配置如何，先把主题层面可能注入的 qrcode.min.js 全部移除，保证后续逻辑可控。
   */
  QR_REGEX.lastIndex = 0;               // 重置全局正则的游标，防止漏删
  const cleaned = html.replace(QR_REGEX, '');

  /**
   * 读取主题配置：
   * - themeCfg.reward.enable：是否开启“打赏/扫码”（历史上该开关却未真正控制脚本加载）；
   * - themeCfg.ptool.share_mobile：是否渲染“手机扫码阅读”工具。
   *
   * needQRCode 为真表示“本页面有潜在需求”，但仍需结合页面是否真的渲染了 #qrcode 容器再决定是否注入脚本。
   */
  const themeCfg = hexo.theme.config || {};
  const needQRCode =
    Boolean(themeCfg.reward && themeCfg.reward.enable) ||
    Boolean(themeCfg.ptool && themeCfg.ptool.share_mobile);

  /**
   * 二次判定：即使配置需要，但如果页面未包含目标容器（id="qrcode"），也不注入脚本。
   * 原因：
   * - 某些页面（如列表页、首页）通常不会渲染扫码容器，提前过滤可避免无用请求；
   * - “需要 + 存在容器”同时满足，才说明脚本“此时此地确实有用”。
   */
  if (!needQRCode || !cleaned.includes('id="qrcode"')) {
    // 不需要或没有容器：保持“剥离后”的干净版本，直接返回。
    return cleaned;
  }

  /**
   * 【阶段二：有的放矢地注入】
   * - 仅当页面包含 #qrcode 且配置开启时，把脚本附加到 </body> 前；
   * - 放在文档尾部可确保 DOM 已就绪，且与 PJAX 行为兼容；
   * - 以 replace('</body>', ...) 的方式保证“只注入一次”且位置稳定。
   */
  return cleaned.replace('</body>', `${QR_TAG}\n</body>`);
});

hexo.extend.filter.register('theme_inject:bottom', () => {
  /**
   * 在主题底部注入一段“守护”脚本，给 anzhiyu.qrcodeCreate() 加一层保险：
   * - 主题 main.js 会无条件调用 anzhiyu.qrcodeCreate()；
   * - 当我们按需未加载 qrcode.min.js 时，global QRCode 不存在，直接调用会报错；
   * - 这里把原函数包一层，若未定义 QRCode，则静默返回（no-op），避免控制台报错。
   *
   * 放在 bottom 的原因：
   * - 不影响首屏结构与样式；
   * - 早于主题的功能脚本执行时机即可生效（确保覆盖原函数）。
   */
  return `<script>
    (function () {
      // 若主题全局对象不存在或函数未定义，说明主题版本或加载顺序不同，直接跳过，避免二次修改。
      if (!window.anzhiyu || typeof anzhiyu.qrcodeCreate !== 'function') return;

      // 保存原始实现，便于在满足条件时正常调用。
      var original = anzhiyu.qrcodeCreate;

      // 包装：仅在全局 QRCode 已可用时才真正执行生成逻辑。
      anzhiyu.qrcodeCreate = function () {
        // 当按需未加载 qrcode.min.js 时，这里为 undefined，直接 no-op。
        if (typeof QRCode === 'undefined') return;
        // 保持 this 语义与入参不变，尽量无侵入。
        return original.apply(this, arguments);
      };
    })();
  </script>`;
});