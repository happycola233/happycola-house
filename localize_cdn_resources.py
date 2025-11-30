# -*- coding: utf-8 -*-
"""
本脚本用于将 anzhiyu 主题的第三方依赖从外部 CDN 批量下载到本地 Hexo 工程中，
以便在配置 CDN 为 local 时，所有资源都从自己服务器（/pluginsSrc）加载，而不是走外网 CDN。

主要功能：
1. 根据脚本中的 PLUGINS 列表，
   按 anzhiyu 主题使用的 cbd CDN 规则：
       https://cdn.cbd.int/${name}@${version}/${file}
   批量下载对应的 JS / CSS 等文件到：
       source/pluginsSrc/${name}/${file}
   这与主题本地模式使用的路径 /pluginsSrc/${name}/${file 一一对应}。

2. 自动扫描下载到本地的 CSS 文件内容，
   解析其中的 url(...) 引用（如字体、背景图等），
   再按相对路径下载这些静态资源到与 CSS 同级的本地目录，
   用于消除诸如：
       /pluginsSrc/@fortawesome/fontawesome-free/webfonts/*.woff2
       /pluginsSrc/anzhiyu-theme-static/icon/*.woff2
   之类的 404。

3. 通过 EXTRA_CSS 列表额外下载某些不走 plugins.yml、
   但在主题配置里单独引用的 CSS，例如：
       icons.fontawesome_animation_css
   同样会自动扫描并下载其依赖的字体 / 图片资源。

使用方式（默认脚本放在 Hexo 根目录）：
1. 确认本地已有 Python 3。
2. 将本文件保存为 download_plugins.py（文件名可自定义）。
3. 在 Hexo 根目录执行：
       python download_plugins.py
4. 脚本会在 source/pluginsSrc 下创建相应目录并写入文件。
   运行完成后，配合主题配置：
       CDN.internal_provider: local
       CDN.third_party_provider: local
   以及各项指向 /pluginsSrc/... 的本地路径，
   即可让站点在本地 / 服务器上不再依赖外部 CDN 加载这些资源。
"""


import os
import re
from urllib import request, error
from urllib.parse import urljoin, urlparse

# 和 anzhiyu 主题里 cbd 的写法保持一致：
# https://cdn.cbd.int/${name}@${version}/${file}
BASE_URL = "https://cdn.cbd.int"

# ===== 从 plugins.yml 抄出来的配置 =====
PLUGINS = [
    {"id": "algolia_search", "name": "algoliasearch", "file": "dist/algoliasearch-lite.umd.js", "version": "4.18.0"},
    {"id": "instantsearch", "name": "instantsearch.js", "file": "dist/instantsearch.production.min.js", "version": "4.60.0"},
    {"id": "docsearch_js", "name": "@docsearch/js", "file": "dist/umd/index.js", "version": "3.5.2"},
    {"id": "docsearch_css", "name": "@docsearch/css", "file": "dist/style.css", "version": "3.5.2"},
    {"id": "pjax", "name": "pjax", "file": "pjax.min.js", "version": "0.2.8"},
    {"id": "blueimp_md5", "name": "blueimp-md5", "file": "js/md5.min.js", "version": "2.19.0"},
    {"id": "valine", "name": "valine", "file": "dist/Valine.min.js", "version": "1.5.1"},
    {"id": "twikoo", "name": "twikoo", "file": "dist/twikoo.all.min.js", "version": "1.6.44"},
    {"id": "waline_js", "name": "@waline/client", "file": "dist/waline.js", "version": "3.1.3"},
    {"id": "waline_css", "name": "@waline/client", "file": "dist/waline.css", "version": "3.1.3"},
    {"id": "waline_meta_css", "name": "@waline/client", "file": "dist/waline-meta.css", "version": "3.1.3"},
    {"id": "sharejs", "name": "butterfly-extsrc", "file": "sharejs/dist/js/social-share.min.js", "version": "1.1.3"},
    {"id": "sharejs_css", "name": "butterfly-extsrc", "file": "sharejs/dist/css/share.min.css", "version": "1.1.3"},
    {"id": "mathjax", "name": "mathjax", "file": "es5/tex-mml-chtml.js", "version": "3.2.2"},
    {"id": "katex", "name": "katex", "file": "dist/katex.min.css", "version": "0.16.0"},
    {"id": "katex_copytex", "name": "katex", "file": "dist/contrib/copy-tex.min.js", "version": "0.16.0"},
    {"id": "mermaid", "name": "mermaid", "file": "dist/mermaid.min.js", "version": "10.2.4"},
    {"id": "canvas_ribbon", "name": "butterfly-extsrc", "file": "dist/canvas-ribbon.min.js", "version": "1.1.3"},
    {"id": "canvas_fluttering_ribbon", "name": "butterfly-extsrc", "file": "dist/canvas-fluttering-ribbon.min.js", "version": "1.1.3"},
    {"id": "canvas_nest", "name": "butterfly-extsrc", "file": "dist/canvas-nest.min.js", "version": "1.1.3"},
    {"id": "activate_power_mode", "name": "butterfly-extsrc", "file": "dist/activate-power-mode.min.js", "version": "1.1.3"},
    {"id": "fireworks", "name": "butterfly-extsrc", "file": "dist/fireworks.min.js", "version": "1.1.3"},
    {"id": "click_heart", "name": "butterfly-extsrc", "file": "dist/click-heart.min.js", "version": "1.1.3"},
    {"id": "ClickShowText", "name": "butterfly-extsrc", "file": "dist/click-show-text.min.js", "version": "1.1.3"},
    {"id": "lazyload", "name": "vanilla-lazyload", "file": "dist/lazyload.iife.min.js", "version": "17.8.5"},
    {"id": "instantpage", "name": "instant.page", "file": "instantpage.js", "version": "5.2.0"},
    {"id": "typed", "name": "typed.js", "file": "dist/typed.umd.js", "version": "2.1.0"},
    {"id": "pangu", "name": "pangu", "file": "dist/browser/pangu.min.js", "version": "4.0.7"},
    {"id": "fancybox_css", "name": "@fancyapps/ui", "file": "dist/fancybox/fancybox.css", "version": "5.0.28"},
    {"id": "fancybox", "name": "@fancyapps/ui", "file": "dist/fancybox/fancybox.umd.js", "version": "5.0.28"},
    {"id": "medium_zoom", "name": "medium-zoom", "file": "dist/medium-zoom.min.js", "version": "1.1.0"},
    {"id": "snackbar_css", "name": "node-snackbar", "file": "dist/snackbar.min.css", "version": "0.1.16"},
    {"id": "snackbar", "name": "node-snackbar", "file": "dist/snackbar.min.js", "version": "0.1.16"},
    {"id": "fontawesome", "name": "@fortawesome/fontawesome-free", "file": "css/all.min.css", "version": "6.4.0"},
    {"id": "flickr_justified_gallery_js", "name": "flickr-justified-gallery", "file": "dist/fjGallery.min.js", "version": "2.1.2"},
    {"id": "flickr_justified_gallery_css", "name": "flickr-justified-gallery", "file": "dist/fjGallery.css", "version": "2.1.2"},
    {"id": "aplayer_css", "name": "anzhiyu-theme-static", "file": "aplayer/APlayer.min.css", "version": "1.0.0"},
    {"id": "aplayer_js", "name": "anzhiyu-blog-static", "file": "js/APlayer.min.js", "version": "1.0.1"},
    {"id": "meting_js", "name": "hexo-anzhiyu-music", "file": "assets/js/Meting2.min.js", "version": "1.0.1"},
    {"id": "prismjs_js", "name": "prismjs", "file": "prism.js", "version": "1.29.0"},
    {"id": "prismjs_lineNumber_js", "name": "prismjs", "file": "plugins/line-numbers/prism-line-numbers.min.js", "version": "1.29.0"},
    {"id": "prismjs_autoloader", "name": "prismjs", "file": "plugins/autoloader/prism-autoloader.min.js", "version": "1.29.0"},
    {"id": "artalk_js", "name": "artalk", "file": "dist/Artalk.js", "version": "2.6.4"},
    {"id": "artalk_css", "name": "artalk", "file": "dist/Artalk.css", "version": "2.6.4"},
    {"id": "pace_js", "name": "pace-js", "file": "pace.min.js", "version": "1.2.4"},
    {"id": "pace_default_css", "name": "anzhiyu-theme-static", "file": "progress_bar/progress_bar.css", "version": "1.1.10"},
    {"id": "coin_js", "name": "anzhiyu-theme-static", "file": "coin/coin.js", "version": "1.0.0"},
    {"id": "coin_css", "name": "anzhiyu-theme-static", "file": "coin/coin.min.css", "version": "1.0.0"},
    {"id": "countup_js", "name": "anzhiyu-theme-static", "file": "countup/countup.js", "version": "1.0.0"},
    {"id": "gsap_js", "name": "anzhiyu-theme-static", "file": "gsap/gsap.min.js", "version": "1.0.0"},
    {"id": "rightmenu", "name": "anzhiyu-theme-static", "file": "rightmenu/rightmenu.js", "version": "1.0.0"},
    {"id": "waterfall", "name": "anzhiyu-theme-static", "file": "waterfall/waterfall.js", "version": "1.0.0"},
    {"id": "ali_iconfont_css", "name": "anzhiyu-theme-static", "file": "icon/ali_iconfont_css.css", "version": "1.1.9"},
    {"id": "accesskey_js", "name": "anzhiyu-theme-static", "file": "accesskey/accesskey.js", "version": "1.1.5"},
    {"id": "colorthief", "name": "colorthief", "file": "dist/color-thief.umd.min.js", "version": "2.6.0"},
    {"id": "swiper_css", "name": "anzhiyu-theme-static", "file": "swiper/swiper.min.css", "version": "1.0.0"},
    {"id": "swiper_js",  "name": "anzhiyu-theme-static", "file": "swiper/swiper.min.js",  "version": "1.0.0"},
]

# 额外从配置里单独引用的 CSS（当前只有 fontawesome_animation_css）
EXTRA_CSS = [
    {
        "id": "fontawesome_animation_css",
        "url": "https://npm.elemecdn.com/hexo-butterfly-tag-plugins-plus@1.0.17/lib/assets/font-awesome-animation.min.css",
        # 存在 source/pluginsSrc/font-awesome-animation/font-awesome-animation.min.css
        "relative": "font-awesome-animation/font-awesome-animation.min.css",
    }
]


def build_url(name: str, version: str, file_path: str) -> str:
    """
    构造 cbd CDN 地址：
    https://cdn.cbd.int/${name}@${version}/${file}
    """
    file_path = file_path.lstrip("/")
    return f"{BASE_URL}/{name}@{version}/{file_path}"


def build_local_path(root: str, name: str, file_path: str) -> str:
    """
    构造本地保存路径，对应 /pluginsSrc/${name}/${file}
    """
    relative = f"{name}/{file_path.lstrip('/')}"
    parts = relative.split("/")
    return os.path.join(root, *parts)


def download_file(url: str, dest: str, timeout: int = 30) -> bool:
    """
    下载单个文件
    """
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    try:
        print(f"-> {url}")
        with request.urlopen(url, timeout=timeout) as resp, open(dest, "wb") as f:
            f.write(resp.read())
        print(f"   Saved to {dest}")
        return True
    except error.HTTPError as e:
        print(f"   [HTTP {e.code}] Failed to download {url}")
    except error.URLError as e:
        print(f"   [URL Error] Failed to download {url}: {e.reason}")
    except Exception as e:
        print(f"   [Error] Failed to download {url}: {e}")
    return False


def download_css_assets(local_css_path: str, remote_css_url: str):
    """
    扫描本地 CSS 里的 url(...)，把其中引用的静态资源也下载下来。
    例如：
      - ../webfonts/fa-solid-900.woff2
      - font_2508400_fpn9ui60u6q.woff2?t=1690446183540
    """
    print(f"   [CSS] Scan assets in {local_css_path}")
    try:
        try:
            text = open(local_css_path, "r", encoding="utf-8").read()
        except UnicodeDecodeError:
            text = open(local_css_path, "r", encoding="latin-1").read()
    except Exception as e:
        print(f"   [CSS] Cannot read {local_css_path}: {e}")
        return

    css_dir = os.path.dirname(local_css_path)
    pattern = re.compile(r"url\(([^)]+)\)")

    for m in pattern.finditer(text):
        raw = m.group(1).strip().strip('\'"')
        if not raw:
            continue
        # 忽略绝对地址和 data: URI
        if raw.startswith(("data:", "http://", "https://", "//")):
            continue

        # 远程资源 URL（相对 CSS 所在路径）
        asset_remote = urljoin(remote_css_url, raw)
        # 本地保存路径：相对 CSS 文件目录
        parsed = urlparse(raw)
        asset_rel_path = parsed.path  # 去掉 ?t= 这类 query
        dest_path = os.path.normpath(os.path.join(css_dir, asset_rel_path))

        if os.path.exists(dest_path):
            # 已存在就跳过
            continue

        print(f"   [CSS asset] {asset_remote}")
        download_file(asset_remote, dest_path)


def main():
    # 默认脚本放在 Hexo 根目录
    base_dir = os.path.dirname(os.path.abspath(__file__))
    target_root = os.path.join(base_dir, "source", "pluginsSrc")

    print(f"Target root: {target_root}")
    success = 0
    failed = 0

    # 1. 下载 plugins.yml 中的所有文件
    for p in PLUGINS:
        name = p["name"]
        version = p["version"]
        file_path = p["file"]

        print(f"\n[{p['id']}]")
        remote_url = build_url(name, version, file_path)
        dest = build_local_path(target_root, name, file_path)

        if download_file(remote_url, dest):
            success += 1
            # 如果是 CSS，同步下载它引用的资源（字体等）
            if file_path.lower().endswith(".css"):
                download_css_assets(dest, remote_url)
        else:
            failed += 1

    # 2. 下载额外的 CSS（例如 fontawesome_animation_css）
    for e in EXTRA_CSS:
        print(f"\n[{e['id']}] (extra css)")
        remote_url = e["url"]
        dest = os.path.join(target_root, *e["relative"].split("/"))

        if download_file(remote_url, dest):
            success += 1
            download_css_assets(dest, remote_url)
        else:
            failed += 1

    print("\nDone.")
    print(f"Success: {success}, Failed: {failed}")


if __name__ == "__main__":
    main()
