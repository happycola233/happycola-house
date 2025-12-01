---
title: "Hexo + 安知鱼主题：一篇搞懂 front-matter 配置"
date: 2025-11-19 23:01:16
updated: 
published: true
categories:
  - 博客相关
tags:
  - Hexo
  - frontmatter
  - anzhiyu
  - 安知鱼
keywords:
  - Hexo
  - frontmatter
  - anzhiyu
  - 安知鱼
description: "详细介绍 Hexo 博客中 front-matter 的概念和用法，结合安知鱼（anzhiyu）主题逐个解析常用字段，并附可直接复制的文章模板。"
cover: /img/posts/default_cover/default_cover_2.png
---

# Hexo + 安知鱼主题：一篇搞懂 front-matter 配置

在用 Hexo 写博客的时候，你可能早就习惯了每篇文章开头那一块：

```yaml
---
title: Hello World
date: 2025-01-01 10:00:00
---
```

这一块就是 **front-matter**。如果你用的是 **Hexo + 安知鱼（anzhiyu）主题**，那么 front-matter 不仅决定了文章的标题和时间，还能控制封面图、目录、评论、AI 摘要等一大堆细节。

这篇文章就来系统讲讲：

* front-matter 是什么
* Hexo 原生的常用字段
* 安知鱼主题扩展出来的字段
* 一份可直接复制的 front-matter 模板

---

## 一、front-matter 到底是什么？

官方定义：**front-matter 是写在文章开头的一段配置块，用来描述这篇内容的各种信息**。Hexo 支持 YAML 或 JSON 格式，最常用的是 YAML，也就是 `---` 包起来的那种。

典型样子：

```yaml
---
title: "Hello World"
date: 2013/7/13 20:46:25
---
正文从这里开始……
```

* **位置**：文件最顶部
* **作用**：给文章打上「元数据」（metadata），比如标题、时间、分类、标签、封面等
* **语法**：YAML，注意缩进、冒号后要有空格、列表用 `-`

在 Hexo 里，每篇文章都会被解析成一个 `page`/`post` 对象，front-matter 写的字段都会变成 `page.xxx`，可以在主题模板中被访问和使用。

---

## 二、Hexo 原生 front-matter 字段

先看 Hexo 自带的通用字段，不依赖任何主题。

### 1. 基础字段：layout / title / date / updated / lang / published

```yaml
layout: post
title: "这是一篇示例文章"
date: 2025-01-01 10:00:00
updated: 2025-01-02 09:30:00
lang: zh-CN
published: true
comments: true
```

* **layout**

  * 用来指定使用哪种布局。
  * 常见值：`post`（文章）、`page`（独立页面）。
  * 默认值：`_config.yml` 里的 `default_layout`。

* **title**

  * 文章标题，对应 `page.title`。
  * 默认：文件名，但**强烈建议手动写**，方便 SEO 和阅读。

* **date**

  * 文章创建时间，对应 `page.date`。
  * 如果不写，Hexo 会用 **文件创建时间** 作为默认值。

* **updated**

  * 文章更新时间，对应 `page.updated`。
  * 不写时通常使用文件修改时间。
  * 有比较大改动时建议手动更新一下。

* **lang**

  * 指定本文语言，比如 `zh-CN`、`en`。
  * 默认继承站点 `_config.yml` 中的 `language`。

* **published**

  * 是否发布文章。
  * `true`：正常发布（_posts 下默认如此）。
  * `false`：文章处于草稿状态（_drafts 下默认如此）。

* **comments**

  * 是否开启评论。
  * `true` / `false`。
  * 如果主题支持，会用这个字段控制评论模块。

---

### 2. 分类 & 标签：categories / tags

```yaml
categories:
  - 学习笔记
  - 前端
tags:
  - Hexo
  - Front-matter
  - Anzhiyu
```

* **categories**

  * 文章分类，支持多级：

    * 单层：`categories: 学习笔记`
    * 多层：如示例，会被解析为「学习笔记 / 前端」。
  * 在很多主题里，会生成分类页，并用于侧边栏分类导航。

* **tags**

  * 文章标签，支持多个。
  * 常用于标签云页面、文章底部标签列表等。

---

### 3. 链接 & 摘要：permalink / excerpt / disableNunjucks

```yaml
permalink: /hexo/front-matter-intro.html
excerpt: "这一篇主要介绍 Hexo + 安知鱼主题下的 front-matter 配置用法。"
disableNunjucks: false
```

* **permalink**

  * 覆盖默认生成的文章链接。
  * 要么以 `/` 结尾：`/hexo/front-matter/`
  * 要么以 `.html` 结尾：`/hexo/front-matter.html`
  * 不写就走 `_config.yml` 里的 `permalink` 模板。

* **excerpt**

  * 纯文本摘要。
  * 一般需要配合插件或主题支持，有的主题会直接用它作为列表页摘要。

* **disableNunjucks**

  * 是否禁用本篇文章中的 Nunjucks 渲染（`{{ }}`、`{% %}` 那套）。
  * 有时你只想写出 `{{ text }}` 这种字符而不希望被渲染，就可以设置为 `true`。

---

## 三、安知鱼主题的扩展 front-matter 字段

安知鱼主题是在 Butterfly 的基础上二次开发的，对文章 front-matter 做了很多增强，主要集中在：外观、目录、版权、数学公式、播放器、AI 摘要等。

下面这些字段**不是 Hexo 内置**的，而是被安知鱼主题读取后，用来控制页面表现。

### 1. SEO 相关：keywords / description / ai

```yaml
keywords:
  - Hexo
  - 安知鱼
  - Front-matter
description: "详细讲解 Hexo + 安知鱼主题中 front-matter 的用法与常见字段。"
ai: "本文通过实例讲解 front-matter 的作用，帮助你快速配置 Hexo 博客。"
```

* **keywords**

  * 文章关键字。
  * 通常会写入 `<meta name="keywords">`，对 SEO 有一定帮助。

* **description**

  * 文章描述。
  * 主题通常会用作 `<meta name="description">`，也可能在文章列表的简介中展示。

* **ai**

  * 文章 AI 摘要。
  * 安知鱼主题支持 AI 摘要展示，这个字段可以填你生成的简短总结。

---

### 2. 封面 & 样式：top_img / cover / main_color / swiper_index / top_group_index

```yaml
top_img: https://example.com/images/post-top.jpg
cover: https://example.com/images/post-cover.jpg
main_color: "#409EFF"
swiper_index: 1
top_group_index: 2
```

* **top_img**

  * 文章顶部大图（Banner）。
  * 一般显示在文章页顶部横幅位置。

* **cover**

  * 文章缩略图。
  * 常用于首页文章卡片、列表、推荐位等。
  * 如果没有设置 `top_img`，部分主题会直接使用 `cover` 作为文章页顶部图。
  * 可以设为：

    * 图片链接：使用该图
    * `false`：本篇不显示封面
    * 留空：走主题默认策略（默认封面或不显示）

* **main_color**

  * 文章主色调。
  * 必须是**完整 6 位 16 进制颜色**，例如 `#ffffff`，不能写成 `#fff`。
  * 安知鱼会用它来渲染按钮、标题高亮等，让某篇文章有自己的主色风格。

* **swiper_index**

  * 控制首页轮播图中的排序。
  * 数字越小越靠前。
  * 不填或留空：不加入轮播。

* **top_group_index**

  * 控制首页右侧卡片组中的排序。
  * 数字越小越靠前。
  * 通常用于「置顶推荐」或者「精选文章」区域。

---

### 3. 阅读体验：comments / toc / toc_number / toc_style_simple / highlight_shrink / aside

```yaml
comments: true
toc: true
toc_number: true
toc_style_simple: false
highlight_shrink: false
aside: true
```

这些字段通常是对**主题全局配置的覆盖**，只作用于当前文章。

* **comments**

  * 是否显示评论模块。
  * 默认跟随主题全局配置，写在 front-matter 中可以对单篇文章关闭/开启评论。

* **toc**

  * 是否显示目录（Table of Contents）。
  * `true`：显示
  * `false`：隐藏
  * 不写：沿用主题配置 `toc.enable`。

* **toc_number**

  * 是否显示目录数字编号（如 1.、1.1、1.2）。
  * 不写则沿用 `toc.number`。

* **toc_style_simple**

  * 是否启用简洁版 TOC 风格。
  * 想要更紧凑的目录展示时可以设为 `true`。

* **highlight_shrink**

  * 代码块是否默认折叠。
  * `true`：代码框收起，需要点击展开。
  * `false`：默认展开。
  * 不写时使用主题的 `highlight_shrink` 配置。

* **aside**

  * 是否显示侧边栏。
  * `true`：有右侧侧栏
  * `false`：当前文章不显示侧栏，实现沉浸式阅读。

---

### 4. 版权模块：copyright*

```yaml
copyright: true
copyright_author: "你的名字"
copyright_author_href: "https://your-site.com"
copyright_url: 
copyright_info: "本作品采用 CC BY-NC-SA 4.0 国际许可协议进行许可。"
```

* **copyright**

  * 是否显示文章版权模块。
  * 默认跟随主题配置 `post_copyright.enable`。

* **copyright_author**

  * 版权区显示的作者名。
  * 默认一般会使用站点作者名称（`_config.yml` 或主题配置里）。

* **copyright_author_href**

  * 作者链接。
  * 可指向你的博客首页、GitHub、社交账号等。

* **copyright_url**

  * 版权模块中的文章链接。
  * 通常可留空，主题会自动填充当前文章的永久链接。

* **copyright_info**

  * 版权声明文本。
  * 可以自定义为转载规则、协议说明等文字。

---

### 5. 数学公式 & 音乐播放器：mathjax / katex / aplayer

```yaml
mathjax: false
katex: false
aplayer: false
```

这些字段都是「**按需加载**」的：

* **mathjax**

  * 是否为本篇文章启用 MathJax 渲染公式。
  * 当主题配置里 `mathjax.per_page: false` 时，可以在 front-matter 里为单篇开启。

* **katex**

  * 类似 `mathjax`，只是使用 KaTeX 渲染公式。
  * 哪个生效取决于你在主题里的配置。

* **aplayer**

  * 是否为本页加载 APlayer 的 js 和 css。
  * 用于在文章中插入音乐播放器时使用。

---

## 四、一份可直接复制的 front-matter 模板（Hexo + 安知鱼）

下面这份模板基本包含了你常见会用到的字段，可以当作「全量版」，写文章时按需删减即可。

```yaml
---
########################################
# 基本必需字段（Hexo 原生）
########################################

layout: post
# 【必需】布局类型（在 _posts 文件下的默认就是 post，可缺省）
# - 一般文章用 post
# - 独立页面用 page（如 about、links 等）
# - 默认值：config.default_layout

title: "在这里写文章标题"
# 【必需】文章标题
# - 显示在文章页面标题 & HTML <title> 中
# - 默认值：文件名（不建议依赖默认，最好手动写）

date: 2025-01-01 10:00:00
# 【必需】文章创建日期
# - 格式通常为：YYYY-MM-DD HH:MM:SS
# - 默认值：文件创建日期（建议显式写上）

updated: 2025-01-01 10:00:00
# 【可选】文章更新日期
# - 不写时，默认值为文件最后修改时间
# - 文章有较大改动时可手动更新，方便读者和 RSS

published: true
# 【可选】是否发布文章
# - true：正常发布
# - false：不发布（通常用于 _draft 下的草稿）
# - 默认：_posts 目录下为 true，_draft 下为 false

lang: zh-CN
# 【可选】文章语言，用于覆盖自动检测
# - 默认继承自站点 _config.yml
# - 常用：zh-CN, en, ja 等


########################################
# 分类、标签、永久链接等
########################################

categories:
  - 分类1
  - 子分类A
# 【可选】文章分类（不适用于分页）
# - 支持单层或多层：
#   - 单层：categories: 分类1
#   - 多层：如上所示为「分类1 / 子分类A」
# - 默认：无

tags:
  - 标签1
  - 标签2
# 【可选】文章标签（不适用于分页）
# - 支持多个标签
# - 默认：无

permalink: 
# 【可选】覆盖文章的永久链接（URL）
# - 以 / 或 .html 结尾，例如：
#   /my-custom-url/
#   /notes/hexo-frontmatter.html
# - 默认：按照站点 permalink 规则自动生成
# - 留空或删除则使用默认规则


########################################
# SEO / 摘要 / 关键字描述
########################################

keywords:
  - 关键字1
  - 关键字2
# 【可选】文章关键字
# - 一般用于 SEO，部分主题会注入到 meta keywords
# - 默认：无

description: "这是一段文章的简短描述，用于 SEO 和摘要显示。"
# 【可选】文章描述
# - 显示在 meta description 中
# - 一些主题会在文章列表摘要中使用此字段
# - 默认：无或自动截取正文

excerpt: 
# 【可选】纯文本页面摘要
# - 一般配合相关插件使用（例如 hexo-excerpt 等）
# - 若留空，通常会自动截取正文或忽略


########################################
# 评论、目录、侧边栏等显示控制（视主题而定）
########################################

comments: true
# 【可选】是否显示文章评论模块
# - true：显示评论
# - false：关闭评论
# - 默认：true（由主题或站点配置决定）

toc: true
# 【可选】是否显示 TOC（目录）
# - 默认：继承主题配置（如 theme_config.toc.enable）
# - true/false 用于对单篇文章进行覆盖

toc_number: true
# 【可选】目录前是否显示序号（1.1、1.2 等）
# - 默认：继承主题配置（如 theme_config.toc.number）

toc_style_simple: false
# 【可选】是否使用简洁 TOC 样式
# - true：简洁模式
# - false：正常模式（默认）
# - 是否生效取决于主题是否支持

aside: true
# 【可选】是否显示侧边栏
# - true：显示右侧侧边栏
# - false：本页不显示侧边栏
# - 默认：true（由主题配置决定）


########################################
# 代码高亮 / Math / 播放器（视主题与插件而定）
########################################

highlight_shrink: false
# 【可选】代码框是否折叠
# - true：默认折叠，需要点击展开
# - false：默认展开
# - 默认：主题的 highlight_shrink 设置

mathjax: false
# 【可选】是否启用 MathJax（公式渲染）
# - 当在站点/主题中配置 mathjax.per_page: false 时，
#   可通过此字段为单篇文章开启/关闭
# - true：启用
# - false：关闭
# - 默认：false（由主题全局配置控制）

katex: false
# 【可选】是否启用 KaTeX（公式渲染，MathJax 的替代方案）
# - 同 mathjax，具体行为视主题设置而定
# - true：启用
# - false：关闭
# - 默认：false

aplayer: false
# 【可选】是否在本页加载 aplayer 的 js 和 css
# - 用于文章内插入音乐播放器
# - true：本页加载（需按主题/文档配置音乐）
# - false：不加载
# - 默认：false 或主题配置


########################################
# 主题相关：封面图、顶部图、轮播等（不同主题支持略有差异）
########################################

top_img:
# 【可选】文章顶部大图
# - 通常显示在文章页面顶部大横幅位置
# - 填写图片链接，如：
#   https://example.com/images/post-top.jpg
# - 留空则使用主题默认或不显示

cover:
# 【可选】文章缩略图
# - 通常显示在文章列表卡片中
# - 若 top_img 未设置，一些主题会在文章页顶部使用此缩略图
# - 可选取值：
#   - 图片链接：作为封面图
#   - false：强制本文章不显示封面图
#   - 留空：使用默认策略（如主题默认图或不显示）

swiper_index:
# 【可选】首页轮播图配置索引（仅部分主题支持）
# - 数字越小，在轮播中的位置越靠前
# - 为空或不填：不加入轮播
# - 一般只对少数精选文章设置

top_group_index:
# 【可选】首页右侧卡片组配置索引（仅部分主题支持）
# - 数字越小越靠前
# - 用于将某些文章展示在首页侧边的推荐区

main_color:
# 【可选】文章主色
# - 必须是 6 位 16 进制颜色，不可简写
#   例如：#ffffff 不可写成 #fff
# - 一些主题会用作按钮、标题等高亮颜色
# - 留空则使用主题默认配色


########################################
# 版权信息（多数高级主题支持）
########################################

copyright: true
# 【可选】是否显示文章版权模块
# - true：显示版权信息
# - false：关闭版权模块
# - 默认：继承主题中 post_copyright.enable

copyright_author: "你的名字或昵称"
# 【可选】版权模块中显示的作者
# - 默认：站点作者名（theme 或 _config.yml 中的 author）

copyright_author_href: "https://your-homepage-or-profile.com"
# 【可选】作者链接
# - 可填博客首页、GitHub、社交主页等
# - 不填则可能只显示文字作者名

copyright_url: 
# 【可选】版权模块中的文章链接
# - 一般可留空，由主题自动使用当前文章链接
# - 如需指定自定义链接可在此填写

copyright_info: "本作品采用 CC BY-NC-SA 4.0 国际许可协议进行许可。"
# 【可选】版权声明文字
# - 可自定义为你自己的版权/转载说明
# - 不填则使用主题默认声明或不显示


########################################
# 其他扩展字段（AI 摘要、Nunjucks 控制等）
########################################

ai:
# 【可选】文章 AI 摘要
# - 若你使用某些 AI 摘要功能/插件，可将生成的摘要写在这里
# - 非必须字段，不用可以删除

disableNunjucks: false
# 【可选】是否禁用 Nunjucks 渲染
# - true：禁用本篇文章中的 {{ }} / {% %} 标签和标签插件解析
# - false：正常渲染
# - 当你只是想写出 "{{" 字符本身而不被解析时可以启用

---
```

你可以把这一段直接放进 `scaffolds/post.md`，这样以后每次 `hexo new` 新文章时就会自动带上这套 front-matter 模板，只需要改少数字段就好了。

---

## 补：文章优先级 `sticky` 参数

在 Hexo + 安知鱼 主题中，`sticky` 是用来控制首页文章置顶顺序的 front-matter 参数。它来自 Hexo 官方的 hexo-generator-index 插件，而不是主题自带的功能。

只要在文章的 front-matter 中加入 `sticky: 数字`，这篇文章就会被优先显示在首页列表的前面，并且数值越大，排名越靠前。未设置 `sticky` 的文章等价于 `sticky: 0`。

需要注意的是，`sticky` 只影响首页的文章排序，对归档 / 分类 / 标签页没有影响；同时，要确保项目中安装的是 hexo-generator-index 2.0.0 及以上版本，才能正常使用这一特性。


## 五、写在最后：怎么更舒服地用 front-matter？

简单给几个实践小建议：

1. **真正每篇都要改的字段**：
   `title / date / categories / tags / description / top_img / cover`
   其他字段可以当作「按需开关」。

2. 不常改的配置（比如版权、作者链接、main_color 默认值等），可以写在模板里，之后很少动。

3. 如果你经常写某一类型的文章（比如「学习笔记」「碎碎念」），可以为它们单独建一个 scaffold，甚至在 front-matter 里预设好分类/标签。

4. 调试 front-matter 的时候，如果发现字段不生效：

   * 先确认 YAML 语法有没有错（缩进、冒号后空格、列表写法）。
   * 再看主题文档/源码，确认这个字段是不是被主题使用。
   * 清缓存重新生成：`hexo clean && hexo g && hexo s`。