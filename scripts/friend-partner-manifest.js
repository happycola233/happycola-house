"use strict";

/*
 * 用途：在构建阶段生成伙伴 UID 清单（partner-uids.json），避免前端首屏获取 UID 时的竞态或丢失。
 * 说明：仅写入数字 UID（从 source/_data/link.yml 的 link_list 中提取数字或对象的 mid 字段）。
 */
hexo.extend.generator.register("friend-partner-manifest", function (locals) {
  const linkData = locals.data && locals.data.link;
  if (!Array.isArray(linkData)) return;

  const uidSet = new Set();

  const collect = value => {
    if (!value) return;
    if (typeof value === "object") {
      const mid = value.mid || value.uid;
      if (mid && /^\d+$/.test(String(mid))) uidSet.add(String(mid));
      return;
    }
    if (typeof value === "number" || (typeof value === "string" && /^\d+$/.test(value))) {
      uidSet.add(String(value));
    }
  };

  linkData.forEach(section => {
    if (!section || !Array.isArray(section.link_list)) return;
    section.link_list.forEach(collect);
  });

  return {
    path: "partner-uids.json",
    data: JSON.stringify({ uids: Array.from(uidSet) })
  };
});
