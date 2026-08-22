---
title: "Windows 中没有具体路径的快捷方式：Advertised 与 MSIX/AppX"
date: 2025-11-04 23:59:39
updated: 2026-08-22 15:10:00
published: true
categories:
  - 技术
tags:
  - Windows
  - 快捷方式
  - Advertised Shortcuts
  - MSIX
description: "Windows 快捷方式的目标为什么是灰色的，也看不到 exe 路径？本文介绍两种常见情况：MSI Advertised Shortcut 与使用 AUMID 启动的 MSIX/AppX 应用快捷方式，并说明如何辨别及查找真实程序入口。"
ai: "有些 Windows 快捷方式不直接保存 exe 路径，因此属性页中的目标是灰色的，打开文件所在位置也无法点击。相同的界面现象背后可能是完全不同的机制，常见的有 MSI Advertised Shortcut，以及使用 AUMID 激活的 MSIX/AppX 应用快捷方式。"
cover: /img/posts/Advertised-Shortcuts/Advertised-Shortcuts_cover.png
---

# 🌀 快捷方式为什么没有具体路径？

右键一个 `.lnk` 文件并打开 **属性 → 快捷方式**，有时会看到这些现象：

* “目标”一栏是灰色的，无法编辑；
* “打开文件所在的位置”无法点击；
* 目标显示的不是 `C:\Program Files\...\program.exe`，而是一个应用名或一段标识符。

这并不代表快捷方式损坏，只能说明它不是普通的“文件路径快捷方式”。Windows Shell 可以在 `.lnk` 中保存其他形式的目标，再由对应的系统组件解析和启动。

常见的两种情况是：

1. **MSI Advertised Shortcut**：指向 MSI 的产品、功能或组件；
2. **MSIX/AppX 应用快捷方式**：使用 AUMID（Application User Model ID）激活已注册的应用包。

它们在属性窗口中很像，底层原理却完全不同。因此，**不能仅凭目标框变灰，就认定它是 Advertised Shortcut**。

---

## 📦 1）MSI Advertised Shortcut

**Advertised Shortcut** 是由 **Windows Installer（MSI）** 创建并托管的快捷方式。

它不直接指向某个 `exe`，而是指向 MSI 产品中的 Feature/Component。快捷方式内部包含 **Darwin Descriptor（达尔文描述符）**，Windows Installer 可以通过它找到对应的安装信息。

点击这类快捷方式时，Windows Installer 会先解析该描述符。如果关键组件缺失，它还可能触发修复或补装，也就是常说的 **self-healing（自修复）**。

例如，下面是一个 MSI Advertised Shortcut 的属性页。它的“目标”只显示应用名称，无法编辑，“打开文件所在的位置”也处于禁用状态：

<img src="/img/posts/Advertised-Shortcuts/Topaz-Video-AI-Advertised-Shortcut.png" alt="Topaz Video AI 的 MSI Advertised Shortcut 属性页" style="zoom: 67%;" />

### 为什么这样设计？

* 🔧 **自修复**：关键文件缺失时，可以通过 MSI 重新安装组件；
* 📥 **按需安装**：某些 Feature 可以在首次使用时再安装；
* 🏢 **统一部署**：适合企业环境中由 MSI 管理应用和功能状态。

这类快捷方式的数据来自 MSI 数据库中的 **Shortcut 表（Shortcut Table）**。如果能够控制安装参数，一些安装包可以通过下面的属性禁用 advertised 快捷方式：

```text
DISABLEADVTSHORTCUTS=1
```

这个参数改变的是安装行为，并不能直接把已经存在的 `.lnk` 转换成普通快捷方式。

---

## 🧩 2）MSIX/AppX 应用快捷方式

另一种非常容易被误认为 Advertised Shortcut 的情况，是 **MSIX/AppX 打包应用的快捷方式**。

例如，安装 **Claude Desktop** 后，可以从开始菜单中找到 Claude，并把它拖到桌面。Windows 由此生成的 `.lnk` 就是使用 AUMID 的应用快捷方式，其属性如下：

<img src="/img/posts/Advertised-Shortcuts/Claude-MSIX-Shortcut.png" alt="Claude 的 MSIX 应用快捷方式属性，其中目标为 AUMID" style="zoom: 67%;" />

它的目标不是文件路径，而是：

```text
Claude_pzs8sxrjxfjjc!Claude
```

这是一条 **AUMID（Application User Model ID，应用用户模型 ID）**。通常可以把它理解为：

```text
包族名称!应用 ID
```

Windows 收到这个标识后，会在已注册的应用包中查找对应入口，再由 Shell 激活程序。对于这个例子，系统注册的信息包括：

```text
PackageFamilyName : Claude_pzs8sxrjxfjjc
Application ID    : Claude
Executable        : app\Claude.exe
EntryPoint        : Windows.FullTrustApplication
```

`Windows.FullTrustApplication` 表明它是打包后的桌面程序入口，而不是仅凭 MSIX/AppX 就能断定它是传统意义上的 UWP 应用。

### 为什么不直接写 exe 路径？

应用包通常安装在受保护的目录中，例如：

```text
C:\Program Files\WindowsApps\Claude_1.34493.1.0_x64__pzs8sxrjxfjjc\
```

其中的版本号会随更新变化。如果快捷方式固定指向这一版的 `Claude.exe`，应用升级后路径就可能失效。AUMID 是稳定的应用身份，Windows 可以始终把它解析到当前已注册的版本，并同时保留应用包的身份、权限、通知和卸载信息。

这类快捷方式**不使用 Darwin Descriptor，也不依赖 Windows Installer 的 Feature/Component 自修复机制**，所以它不是 MSI Advertised Shortcut。

可以通过下面的形式启动这个 AUMID：

```powershell
explorer.exe shell:AppsFolder\Claude_pzs8sxrjxfjjc!Claude
```

---

## 🔎 3）怎样区分这两种快捷方式？

| 对比项 | MSI Advertised Shortcut | MSIX/AppX 应用快捷方式 |
| --- | --- | --- |
| 管理组件 | Windows Installer（MSI） | Windows Shell 与应用包部署系统 |
| 内部目标 | Darwin Descriptor、MSI Feature/Component | AUMID |
| 常见显示 | 应用名，目标框不可编辑 | `包族名称!应用ID`，目标框不可编辑 |
| 实际程序位置 | MSI 安装目录 | 通常位于 `WindowsApps` 包目录 |
| 更新后路径 | 通常由 MSI 组件管理 | 包目录版本号可能变化，由 AUMID 解析最新版 |
| 自修复 | 可以触发 MSI self-healing | 不具备 MSI Advertised Shortcut 的自修复机制 |

最直观的线索是目标内容：如果它明显形如 `PackageFamilyName!ApplicationId`，并且“目标位置”显示为 `Applications`，通常就是 MSIX/AppX 应用快捷方式。

还可以使用 PowerShell 读取 Shell 保存的解析目标：

```powershell
$shortcutPath = 'C:\Users\admin\Desktop\Claude.lnk'
$shell = New-Object -ComObject Shell.Application
$folder = $shell.Namespace((Split-Path $shortcutPath))
$item = $folder.ParseName((Split-Path $shortcutPath -Leaf))
$item.ExtendedProperty('System.Link.TargetParsingPath')
```

这个 Claude 快捷方式会返回：

```text
Claude_pzs8sxrjxfjjc!Claude
```

随后可以在开始菜单应用注册信息中查询它：

```powershell
Get-StartApps | Where-Object AppID -eq 'Claude_pzs8sxrjxfjjc!Claude'
```

如果需要查看应用包的安装位置和入口，可继续执行：

```powershell
$package = Get-AppxPackage |
  Where-Object PackageFamilyName -eq 'Claude_pzs8sxrjxfjjc'

$package | Select-Object Name, Version, InstallLocation

(Get-AppxPackageManifest -Package $package.PackageFullName).Package.Applications.Application |
  Select-Object Id, Executable, EntryPoint
```

如果没有 AUMID 特征，而应用又由 MSI 安装，才应进一步检查它是否包含 Darwin Descriptor，或通过 Windows Installer API、MSI 分析工具确认。目标框变灰本身不是充分证据。

---

## 🕵️ 4）怎么找到正在运行的真实 exe？

无论属于哪一种特殊快捷方式，都可以从运行中的进程反查实际文件：

1. 通过快捷方式启动应用；
2. 打开 **任务管理器 → 详细信息**；
3. 右键表头并选择 **选择列**；
4. 勾选 **映像路径名称** 或 **命令行**；
5. 查看对应进程的完整路径。

如果应用使用额外的 Launcher、Updater 或多进程架构，主界面进程的路径通常比第一个启动进程更有参考价值。

对于 MSIX/AppX 应用，直接为当前版本目录中的 exe 创建普通快捷方式通常不够稳妥，因为包升级后目录名可能改变。更适合保留系统创建的 AUMID 快捷方式，或者使用 `shell:AppsFolder\AUMID` 启动。

对于 MSI Advertised Shortcut，可以根据实际需要创建指向 exe 的普通快捷方式，但这样会绕过原快捷方式提供的 MSI 自修复和按需安装能力。

---

## ✅ 总结

看到快捷方式没有具体路径时，正确的判断顺序是：

1. 它不是普通的文件路径快捷方式；
2. 查看目标是否形如 `包族名称!应用ID`；
3. 如果是，则属于使用 AUMID 的 MSIX/AppX 应用快捷方式；
4. 如果不是，再结合安装来源和 Darwin Descriptor 判断是否为 MSI Advertised Shortcut。

**界面表现相同，不代表底层类型相同。**“目标灰色、无法打开文件位置”只是特殊 Shell 快捷方式的共同外观，而不是 Advertised Shortcut 的专属特征。
