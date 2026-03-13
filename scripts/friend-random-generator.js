"use strict";

/*
 * 用途：覆盖 anzhiyu 主题内置的 random 生成器，修复首页/页脚随机友链在 link.yml
 *      混用“完整友链对象”和“纯 UID 条目”时出现 undefined 链接与标题的问题。
 * 说明：保留完整 friend_link_list 供友链页等现有逻辑继续使用，同时额外生成仅包含
 *      有效站点对象的 footer_friend_link_list，专门用于首页页脚随机友链与随机跳转提示。
 */

function normalizeFriendItem(item, fallbackAvatar) {
  if (!item) return null;

  if (typeof item === "object") {
    const mid = item.mid || item.uid || "";
    const name = typeof item.name === "string" ? item.name.trim() : "";
    const link = typeof item.link === "string" ? item.link.trim() : "";
    const avatar = typeof item.avatar === "string" && item.avatar.trim()
      ? item.avatar.trim()
      : fallbackAvatar;

    return {
      mid: mid ? String(mid).trim() : "",
      name: name || (mid ? String(mid).trim() : ""),
      link: link || (mid ? `https://space.bilibili.com/${mid}` : ""),
      avatar,
      descr: typeof item.descr === "string" ? item.descr : "",
      isUidOnly: !name || !link
    };
  }

  const mid = String(item).trim();
  if (!mid) return null;

  return {
    mid,
    name: mid,
    link: `https://space.bilibili.com/${mid}`,
    avatar: fallbackAvatar,
    descr: "",
    isUidOnly: true
  };
}

function collectFriendItems(locals, fallbackAvatar) {
  const sections = Array.isArray(locals?.data?.link) ? locals.data.link : [];
  const items = [];

  sections.forEach(section => {
    if (!section || !Array.isArray(section.link_list)) return;
    section.link_list.forEach(rawItem => {
      const normalized = normalizeFriendItem(rawItem, fallbackAvatar);
      if (normalized) items.push(normalized);
    });
  });

  return items;
}

hexo.extend.filter.register("before_generate", () => {
  hexo.extend.generator.register("random", function (locals) {
    const config = hexo.config.random || {};
    const themeConfig = hexo.theme.config || {};
    const footerConfig = (themeConfig.footer && themeConfig.footer.list) || {};
    const pjaxEn = Boolean(themeConfig.pjax && themeConfig.pjax.enable);
    const randomNumberFriend = footerConfig.randomFriends || 0;
    const fallbackAvatar =
      (themeConfig.error_img && themeConfig.error_img.flink) || "/img/friend_404.gif";

    const posts = [];
    for (const post of locals.posts.data) {
      if (post.random !== false) posts.push(post.path);
    }

    const friendLinkList = collectFriendItems(locals, fallbackAvatar);
    const footerFriendList = friendLinkList.filter(item => !item.isUidOnly && item.name && item.link);

    let result = `var posts=${JSON.stringify(
      posts
    )};function toRandomPost(){
      ${pjaxEn ? "pjax.loadUrl('/'+posts[Math.floor(Math.random() * posts.length)]);" : "window.location.href='/'+posts[Math.floor(Math.random() * posts.length)];"}
    };`;

    if (footerConfig.enable && randomNumberFriend > 0) {
      result += `var friend_link_list=${JSON.stringify(friendLinkList)};
      var footer_friend_link_list=${JSON.stringify(footerFriendList)};
      var refreshNum = 1;
      function pickRandomFriend(list) {
        if (!Array.isArray(list) || !list.length) return null;
        return list[Math.floor(Math.random() * list.length)] || null;
      }
      function friendChainRandomTransmission() {
        const friend = pickRandomFriend(footer_friend_link_list);
        if (!friend) return;
        const { name, link } = friend;
        Snackbar.show({
          text:
            "点击前往按钮进入随机一个友链，不保证跳转网站的安全性和可用性。本次随机到的是本站友链：「" + name + "」",
          duration: 8000,
          pos: "top-center",
          actionText: "前往",
          onActionClick: function (element) {
            element.style.opacity = 0;
            window.open(link, "_blank");
          },
        });
      }
      function addFriendLinksInFooter() {
        var footerRandomFriendsBtn = document.getElementById("footer-random-friends-btn");
        var footerContainer = document.getElementById("friend-links-in-footer");
        if (!footerRandomFriendsBtn || !footerContainer) return;
        footerRandomFriendsBtn.style.opacity = "0.2";
        footerRandomFriendsBtn.style.transitionDuration = "0.3s";
        footerRandomFriendsBtn.style.transform = "rotate(" + 360 * refreshNum++ + "deg)";

        const candidateList = footer_friend_link_list.slice();
        const finalLinkList = [];

        while (candidateList.length && finalLinkList.length < ${randomNumberFriend}) {
          const randomIndex = Math.floor(Math.random() * candidateList.length);
          const friend = candidateList.splice(randomIndex, 1)[0];
          if (friend && friend.name && friend.link) {
            finalLinkList.push(friend);
          }
        }

        let html = finalLinkList
          .map(({ name, link }) => {
            return "<a class='footer-item' href='" + link + "' target='_blank' rel='noopener nofollow'>" + name + "</a>";
          })
          .join("");

        html += "<a class='footer-item' href='/link/'>更多</a>";

        footerContainer.innerHTML = html;

        setTimeout(() => {
          footerRandomFriendsBtn.style.opacity = "1";
        }, 300);
      };`;
    }

    return {
      path: config.path || "anzhiyu/random.js",
      data: result,
    };
  });
});
