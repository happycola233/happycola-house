"use strict";

/*
 * 用途：在 Hexo 渲染阶段把 link_list 里的纯 UID 先转成安全的占位对象，
 *      避免主题 Pug 模板在读取数字时抛错；不会改动 source/_data/link.yml。
 */
hexo.extend.filter.register("template_locals", locals => {
  // 读取友链数据，如果没有则直接返回
  const linkData = locals?.site?.data?.link;
  if (!Array.isArray(linkData)) return locals;

  // 兜底头像：优先使用主题配置的 error_img.flink，否则使用本地占位图
  const fallbackAvatar =
    (locals.theme && locals.theme.error_img && locals.theme.error_img.flink) ||
    "/img/friend_404.gif";

  // 将数字或字符串 UID 转成含必要字段的占位对象，保持模板字段完整
  const normalizeItem = item => {
    if (item && typeof item === "object") return item;
    const mid = (item ?? "").toString().trim();
    return {
      mid,
      name: mid || "伙伴",
      link: mid ? `https://space.bilibili.com/${mid}` : "#",
      avatar: fallbackAvatar,
      descr: ""
    };
  };

  // 对每个分组的 link_list 进行规范化，只影响渲染时的内存数据
  linkData.forEach(section => {
    if (!section || !Array.isArray(section.link_list)) return;
    section.link_list = section.link_list.map(normalizeItem);
  });

  return locals;
});
